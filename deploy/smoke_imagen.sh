#!/usr/bin/env bash
# Prueba de humo de una imagen del SGC: ¿sirve en un entorno limpio? (#54, criterios 5 y 6)
#
# Levanta PostgreSQL 16 y Redis desechables, crea un sitio NUEVO con la imagen, lo migra y
# comprueba tres cosas:
#   1. que el despliegue quedó aplicado sin intervención: permisos y workflows
#      (`sgc.verificacion.run`, grupo «despliegue», sin bloqueantes);
#   2. que la versión que declara la instancia (`sgc.estado.instancia`, #53) es la esperada;
#   3. que el migrate la registró (`migracion.pendiente` en falso).
#
# Uso:  deploy/smoke_imagen.sh <imagen> <version-esperada>
#       deploy/smoke_imagen.sh ghcr.io/sciback/sgc-frappe:1.0.0 1.0.0
#
# No toca nada fuera de lo que crea: red, base y redis se borran al salir, salga bien o mal.
set -euo pipefail

IMAGEN="${1:?uso: smoke_imagen.sh <imagen> <version-esperada>}"
ESPERADA="${2:?uso: smoke_imagen.sh <imagen> <version-esperada>}"
PREFIJO="sgc-smoke-$$"
SITIO="smoke.localhost"

limpiar() {
	docker rm -f "$PREFIJO-pg" "$PREFIJO-redis" >/dev/null 2>&1 || true
	docker network rm "$PREFIJO" >/dev/null 2>&1 || true
}
trap limpiar EXIT

docker network create "$PREFIJO" >/dev/null
docker run -d --name "$PREFIJO-pg" --network "$PREFIJO" --network-alias pg \
	-e POSTGRES_PASSWORD=postgres postgres:16 >/dev/null
docker run -d --name "$PREFIJO-redis" --network "$PREFIJO" --network-alias redis redis:7-alpine >/dev/null

for _ in $(seq 60); do
	docker exec "$PREFIJO-pg" pg_isready -U postgres >/dev/null 2>&1 && break
	sleep 2
done
docker exec "$PREFIJO-pg" pg_isready -U postgres >/dev/null

# Un solo contenedor: el volumen anónimo de `sites` vive lo que vive él.
SALIDA="$(docker run --rm --network "$PREFIJO" "$IMAGEN" bash -c "
set -euo pipefail
bench set-config -g db_host pg >/dev/null
bench set-config -g db_port 5432 >/dev/null
bench set-config -g redis_cache redis://redis:6379 >/dev/null
bench set-config -g redis_queue redis://redis:6379 >/dev/null
bench set-config -g redis_socketio redis://redis:6379 >/dev/null
bench new-site $SITIO --db-type postgres --db-host pg --db-port 5432 \
	--db-root-username postgres --db-root-password postgres \
	--admin-password smoke --install-app sgc
bench --site $SITIO migrate
bench --site $SITIO execute sgc.verificacion.run --kwargs \"{'solo': 'despliegue'}\"
echo \"ESTADO=\$(bench --site $SITIO execute sgc.estado.instancia)\"
")" || { echo "$SALIDA" | tail -60; echo "La imagen no arranca, no migra o deja el despliegue a medias." >&2; exit 1; }

echo "$SALIDA" | grep -E "^(F_DEPLOY_RUN_ALL|OK:|FALLIDOS:|VERIFICACIÓN|BLOQUEANTE|Sin hallazgos)" || true

# f_deploy_run_all no corta el migrate si un paso falla: lo dice en su resumen. Aquí sí corta.
if echo "$SALIDA" | grep -q "^FALLIDOS:"; then
	echo "Prueba de humo fallida: algún paso de f_deploy_run_all falló en el sitio nuevo." >&2
	exit 1
fi

ESTADO="$(echo "$SALIDA" | sed -n 's/^ESTADO=//p' | tail -1)"
python3 - "$ESTADO" "$ESPERADA" <<'PY'
import json
import sys

estado, esperada = json.loads(sys.argv[1]), sys.argv[2]
print(json.dumps(estado, indent=1, ensure_ascii=False))
fallos = []
if estado["version"].get("sgc") != esperada:
	fallos.append(f"la instancia dice ser {estado['version'].get('sgc')!r}, se esperaba {esperada!r}")
if estado["migracion"].get("pendiente") is not False:
	fallos.append(f"el migrate no registró la versión: {estado['migracion']}")
if fallos:
	sys.exit("Prueba de humo fallida: " + "; ".join(fallos))
print(f"Prueba de humo superada: sitio nuevo, despliegue aplicado, versión {esperada} migrada.")
PY
