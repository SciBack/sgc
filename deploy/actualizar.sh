#!/usr/bin/env bash
# Actualizar una instancia del SGC con un corte corto, declarado y visible (#55).
#
# No promete cero corte: con migraciones de esquema eso no se sostiene. Promete que el corte
# se avisó antes, que quien entra ve una página de mantenimiento y no un error, que al terminar
# se comprueba solo, y que volver atrás es un comando probado. El procedimiento completo, con
# sus decisiones, está en docs/despliegue/actualizacion.md.
#
#   actualizar.sh actualizar --proyecto P --sitio S --imagen I [--respaldos DIR] [--sin-aviso "motivo"]
#   actualizar.sh comprobar  --proyecto P --sitio S [--imagen I]
#   actualizar.sh volver     --proyecto P --sitio S [--respaldos DIR] [--restaurar-base]
#
# --proyecto  el proyecto de docker compose de la instancia (`docker compose ls`)
# --sitio     el sitio de Frappe (calidad.ejemplo.edu)
# --imagen    la imagen nueva (ghcr.io/sciback/sgc-frappe:1.2.0)
# --respaldos dónde dejar respaldo y estado (por defecto, <directorio del compose>/respaldos)
#
# Del compose solo se cambia la imagen, en el sitio donde ya esté declarada: el `.env`
# (CUSTOM_IMAGE/CUSTOM_TAG, como en frappe_docker) o el propio fichero de compose. Cada fichero
# que se toca queda copiado al lado como .bak-<fecha>, y `volver` los repone.
#
# Funciona en Linux y en macOS: no usa `sed -i`, que cada uno entiende a su manera.
set -euo pipefail
shopt -s inherit_errexit 2>/dev/null || true

SERVICIOS_BACK=(backend websocket scheduler queue-short queue-long)
SERVICIO_FRONT=frontend
# Frappe guarda site_config en memoria 60 s por proceso (frappe/config.py, site_cache(ttl=60)):
# encender o apagar el modo mantenimiento tarda eso en llegar a los procesos que ya corren.
ESPERA_CONFIG=65

die() { echo "✗ $*" >&2; exit 1; }
paso() { echo; echo "==> $*"; }

ACCION="${1:-}"
[[ "$ACCION" =~ ^(actualizar|comprobar|volver)$ ]] || die "uso: actualizar.sh actualizar|comprobar|volver --proyecto P --sitio S [...] (ver cabecera)"
shift
PROYECTO="" SITIO="" IMAGEN="" RESPALDOS="" SIN_AVISO="" RESTAURAR_BASE=""
while [[ $# -gt 0 ]]; do
	case "$1" in
	--proyecto) PROYECTO="$2"; shift 2 ;;
	--sitio) SITIO="$2"; shift 2 ;;
	--imagen) IMAGEN="$2"; shift 2 ;;
	--respaldos) RESPALDOS="$2"; shift 2 ;;
	--sin-aviso) SIN_AVISO="$2"; shift 2 ;;
	--restaurar-base) RESTAURAR_BASE=1; shift ;;
	*) die "opción desconocida: $1" ;;
	esac
done
[[ -n "$PROYECTO" && -n "$SITIO" ]] || die "faltan --proyecto y --sitio"

# --- El compose de la instancia, leído de sus propios contenedores -------------------------------

contenedor() {
	docker ps -q --filter "label=com.docker.compose.project=$PROYECTO" --filter "label=com.docker.compose.service=$1" | head -1
}
BACKEND="$(contenedor backend)"
[[ -n "$BACKEND" ]] || die "no hay un backend en marcha en el proyecto «$PROYECTO» (docker compose ls)"
etiqueta() { docker inspect "$BACKEND" --format "{{index .Config.Labels \"$1\"}}"; }
DIRECTORIO="$(etiqueta com.docker.compose.project.working_dir)"
IFS=',' read -r -a FICHEROS <<<"$(etiqueta com.docker.compose.project.config_files)"
COMPOSE=(docker compose --project-name "$PROYECTO" --project-directory "$DIRECTORIO")
for f in "${FICHEROS[@]}"; do COMPOSE+=(-f "$f"); done
RESPALDOS="${RESPALDOS:-$DIRECTORIO/respaldos}"
ESTADO_FICHERO="$RESPALDOS/ultima-actualizacion.env"

bench() { docker exec "$(contenedor backend)" bench --site "$SITIO" "$@"; }

# Escribir donde haga falta: los compose de producción suelen ser de root.
como() { if [[ -w "$1" && -w "$(dirname "$1")" ]]; then "${@:2}"; else sudo "${@:2}"; fi; }

# Reescribir un fichero con una expresión de sed, sin `sed -i`. Conserva dueño y permisos.
reescribir() { # fichero expresión
	local tmp
	tmp="$(mktemp)"
	sed -e "$2" "$1" >"$tmp"
	como "$1" cp "$tmp" "$1"
	rm -f "$tmp"
}

imagen_de() { docker inspect "$1" --format '{{.Config.Image}}'; }
version_de_imagen() {
	docker image inspect "$1" --format '{{index .Config.Labels "org.opencontainers.image.version"}}' 2>/dev/null || true
}

esperar_backend() {
	for _ in $(seq 60); do
		[[ -n "$(contenedor backend)" ]] && bench execute frappe.ping >/dev/null 2>&1 && return 0
		sleep 2
	done
	die "el backend no responde tras recrearlo"
}

mantenimiento() { # on|off
	bench set-maintenance-mode "$1"
	echo "    Los procesos que ya corren lo notan en ${ESPERA_CONFIG} s como mucho (caché de site_config)."
}

# --- Cambiar la imagen en el compose -------------------------------------------------------------

TOCADOS=()
cambiar_imagen() { # actual nueva marca → deja en TOCADOS los ficheros cambiados
	local actual="$1" nueva="$2" marca="$3" env="$DIRECTORIO/.env" f
	TOCADOS=()
	for f in "${FICHEROS[@]}"; do
		if grep -qF "$actual" "$f"; then
			como "$f" cp -p "$f" "$f.bak-$marca"
			reescribir "$f" "s|$actual|$nueva|g"
			TOCADOS+=("$f")
		fi
	done
	if [[ ${#TOCADOS[@]} -eq 0 && -f "$env" ]] && grep -q '^CUSTOM_IMAGE=' "$env"; then
		local img tag
		img="$(sed -n 's/^CUSTOM_IMAGE=//p' "$env")"
		tag="$(sed -n 's/^CUSTOM_TAG=//p' "$env")"
		[[ "$img:$tag" == "$actual" ]] || die ".env declara $img:$tag y en marcha está $actual: no sé cuál cambiar"
		como "$env" cp -p "$env" "$env.bak-$marca"
		reescribir "$env" "s|^CUSTOM_IMAGE=.*|CUSTOM_IMAGE=${nueva%:*}|; s|^CUSTOM_TAG=.*|CUSTOM_TAG=${nueva##*:}|"
		TOCADOS+=("$env")
	fi
	[[ ${#TOCADOS[@]} -gt 0 ]] || die "no encuentro dónde se declara la imagen $actual en el compose"

	# Lo que vale es lo que compose resuelve, no lo que creemos haber escrito.
	local resueltas
	resueltas="$("${COMPOSE[@]}" config --images 2>/dev/null)"
	grep -qxF "$nueva" <<<"$resueltas" || die "tras el cambio, compose no resuelve $nueva (resuelve: $(tr '\n' ' ' <<<"$resueltas"))"
	! grep -qxF "$actual" <<<"$resueltas" || die "tras el cambio, compose sigue resolviendo $actual en algún servicio"
}

# --- Comprobar ------------------------------------------------------------------------------------

comprobar() { # [imagen esperada]
	local imagen="${1:-}" esperada="" fallos=0 estado servicio c
	if [[ -n "$imagen" ]]; then
		paso "Imagen de cada servicio"
		for servicio in "${SERVICIOS_BACK[@]}" "$SERVICIO_FRONT"; do
			c="$(contenedor "$servicio")"
			if [[ -z "$c" ]]; then
				echo "✗ $servicio: no está en marcha"; fallos=1
			elif [[ "$(imagen_de "$c")" != "$imagen" ]]; then
				echo "✗ $servicio: corre $(imagen_de "$c"), no $imagen"; fallos=1
			else
				echo "    ✓ $servicio: $imagen"
			fi
		done
		esperada="$(version_de_imagen "$imagen")"
	fi
	paso "Verificación de instancia (sgc.verificacion.run)"
	if ! bench execute sgc.verificacion.run; then
		echo "✗ La verificación encontró BLOQUEANTES."; fallos=1
	fi
	paso "Estado de la instancia (sgc.estado.instancia)"
	estado="$(bench execute sgc.estado.instancia 2>/dev/null | tail -1)" || estado=""
	if [[ -z "$estado" ]]; then
		echo "✗ La instancia no responde a sgc.estado.instancia (¿versión anterior a la 1.0.0?)."; fallos=1
	else
		python3 - "$estado" "$esperada" <<'PY' || fallos=1
import json, sys
estado, esperada = json.loads(sys.argv[1]), sys.argv[2]
print(json.dumps(estado, indent=1, ensure_ascii=False))
mal = []
version = estado.get("version", {}).get("sgc")
if esperada and version != esperada:
	mal.append(f"la instancia dice {version!r} y la imagen es la {esperada!r}")
if estado.get("migracion", {}).get("pendiente") is not False:
	mal.append("el migrate no registró la versión del código")
for bloque, datos in estado.items():
	if datos.get("estado") == "error":
		mal.append(f"el bloque «{bloque}» no se pudo calcular ({datos.get('tipo')})")
if mal:
	print("✗ " + "\n✗ ".join(mal))
	sys.exit(1)
PY
	fi
	return "$fallos"
}

que_hacer_si_falla() {
	cat <<EOF

────────────────────────────────────────────────────────────────────────────
La comprobación posterior NO ha pasado. El sitio sigue en MODO MANTENIMIENTO:
nadie trabaja sobre algo que puede estar a medias.

  1. Lee lo que falló arriba. Un AVISO no es motivo de volver; un BLOQUEANTE,
     un servicio con otra imagen o una versión que no cuadra, sí.
  2. Si se arregla sin cambiar de imagen (un paso de f_deploy_run_all que falló,
     una caché), arréglalo, repite la comprobación y quita el mantenimiento:
       $0 comprobar --proyecto $PROYECTO --sitio $SITIO --imagen $IMAGEN
       docker exec \$(docker ps -q -f label=com.docker.compose.project=$PROYECTO -f label=com.docker.compose.service=backend) bench --site $SITIO set-maintenance-mode off
  3. Si no, vuelve a la imagen anterior:
       $0 volver --proyecto $PROYECTO --sitio $SITIO
     y, si esta versión cambiaba el esquema (MAYOR en el CHANGELOG) o la vuelta
     da bloqueantes, además la base y los ficheros del respaldo previo:
       SGC_DB_ROOT_USER=… SGC_DB_ROOT_PASSWORD=… $0 volver --proyecto $PROYECTO --sitio $SITIO --restaurar-base
────────────────────────────────────────────────────────────────────────────
EOF
}

# --- Acciones -------------------------------------------------------------------------------------

actualizar() {
	[[ -n "$IMAGEN" ]] || die "falta --imagen"
	local actual marca dir_respaldo version_nueva
	actual="$(imagen_de "$BACKEND")"
	marca="$(date +%Y%m%d_%H%M%S)"
	[[ "$actual" != "$IMAGEN" ]] || die "la instancia ya corre $IMAGEN"

	paso "1/8 Imagen nueva: $IMAGEN"
	docker image inspect "$IMAGEN" >/dev/null 2>&1 || docker pull "$IMAGEN"
	version_nueva="$(version_de_imagen "$IMAGEN")"
	[[ -n "$version_nueva" ]] || die "la imagen no lleva la etiqueta org.opencontainers.image.version: no es una imagen publicada (#54)"
	echo "    versión $version_nueva (en marcha: $actual)"

	paso "2/8 Aviso a los usuarios"
	if [[ -n "$SIN_AVISO" ]]; then
		echo "    Sin aviso previo, por decisión de quien actualiza: $SIN_AVISO"
	else
		local aviso
		aviso="$(bench execute sgc.mantenimiento.ventana_avisada 2>/dev/null | tail -1)" ||
			die "la versión en marcha no sabe comprobar el aviso (anterior a la 1.0.0). Confirma que se avisó y repite con --sin-aviso \"motivo\""
		echo "    $aviso"
		python3 -c 'import json,sys; sys.exit(0 if json.loads(sys.argv[1]).get("avisado") else 1)' "$aviso" ||
			die "no hay un Comunicado «Mantenimiento programado» enviado que cubra este momento (#92). Avisa con 24 h, o usa --sin-aviso \"motivo\" para una corrección urgente"
	fi

	paso "3/8 Modo mantenimiento"
	mantenimiento on
	# El respaldo va DESPUÉS de que nadie pueda escribir: si hubiera que restaurarlo, no se
	# pierde nada de lo que se guardó entre el respaldo y el corte.
	echo "    Esperando ${ESPERA_CONFIG} s a que lo noten todos los procesos antes de respaldar…"
	sleep "$ESPERA_CONFIG"

	paso "4/8 Respaldo previo (base y ficheros)"
	dir_respaldo="$RESPALDOS/$marca"
	mkdir -p "$dir_respaldo" 2>/dev/null || sudo mkdir -p "$dir_respaldo"
	# Con la imagen NUEVA, sobre los volúmenes y la red del backend en marcha: su cliente
	# PostgreSQL es el que se comprobó al construirla. El de una imagen anterior puede no servir
	# (pg_dump 15 se niega a respaldar un servidor 16, y Frappe lo dice sin fallar).
	local salida ruta
	if ! salida="$(docker run --rm --volumes-from "$BACKEND" --network "container:$BACKEND" "$IMAGEN" \
		bench --site "$SITIO" backup --with-files 2>&1)" || grep -q "Backup failed" <<<"$salida"; then
		echo "$salida" | tail -15
		die "el respaldo falló: no se sigue sin respaldo (el sitio queda en mantenimiento; quítalo a mano si no vas a reintentar)"
	fi
	grep -E "Database|Public|Private|Config" <<<"$salida" || true
	while read -r ruta; do
		[[ -n "$ruta" ]] || continue
		docker cp "$BACKEND:/home/frappe/frappe-bench/sites/$ruta" - | como "$dir_respaldo" tar -x -C "$dir_respaldo"
	done < <(grep -oE "${SITIO//./\\.}/private/backups/[^ ]+" <<<"$salida" | sort -u)
	compgen -G "$dir_respaldo/*-database.sql.gz" >/dev/null || die "el respaldo no salió del contenedor: no se sigue sin respaldo"
	echo "    en $dir_respaldo"

	paso "5/8 Cambiar la imagen y recrear el backend (el frontend sigue sirviendo la página)"
	cambiar_imagen "$actual" "$IMAGEN" "$marca"
	printf '    cambiado: %s\n' "${TOCADOS[@]}"
	como "$RESPALDOS" tee "$ESTADO_FICHERO" >/dev/null <<EOF
MARCA=$marca
ANTERIOR=$actual
NUEVA=$IMAGEN
RESPALDO=$dir_respaldo
FICHEROS_TOCADOS="${TOCADOS[*]}"
EOF
	"${COMPOSE[@]}" up -d --no-deps "${SERVICIOS_BACK[@]}"
	esperar_backend

	paso "6/8 Migrar"
	# clear-cache ANTES: si la versión retira un módulo, migrate leería de Redis la lista vieja.
	bench clear-cache
	if ! bench migrate; then
		echo "✗ El migrate falló."
		que_hacer_si_falla
		exit 1
	fi
	bench clear-cache

	paso "7/8 Recrear el frontend (assets nuevos; unos segundos de corte)"
	"${COMPOSE[@]}" up -d --no-deps "$SERVICIO_FRONT"

	paso "8/8 Comprobación posterior"
	if ! comprobar "$IMAGEN"; then
		que_hacer_si_falla
		exit 1
	fi
	mantenimiento off
	echo
	echo "✓ $SITIO actualizado a $version_nueva ($IMAGEN). Respaldo previo en $dir_respaldo."
}

volver() {
	[[ -f "$ESTADO_FICHERO" ]] || die "no hay $ESTADO_FICHERO: no sé a qué volver"
	# Define MARCA, ANTERIOR, NUEVA, RESPALDO y FICHEROS_TOCADOS.
	# shellcheck source=/dev/null
	. "$ESTADO_FICHERO"
	# shellcheck disable=SC2153
	: "${MARCA:?} ${ANTERIOR:?} ${NUEVA:?} ${RESPALDO:?} ${FICHEROS_TOCADOS:?}"
	local actual f
	actual="$(imagen_de "$BACKEND")"
	[[ "$actual" == "$NUEVA" ]] || die "en marcha está $actual, no $NUEVA: la última actualización no es la que corre"

	paso "Volver de $NUEVA a $ANTERIOR"
	mantenimiento on
	for f in $FICHEROS_TOCADOS; do
		[[ -f "$f.bak-$MARCA" ]] || die "falta la copia $f.bak-$MARCA"
		como "$f" cp -p "$f.bak-$MARCA" "$f"
		echo "    repuesto: $f"
	done
	"${COMPOSE[@]}" config --images 2>/dev/null | grep -qxF "$ANTERIOR" || die "tras reponer, compose no resuelve $ANTERIOR"
	"${COMPOSE[@]}" up -d --no-deps "${SERVICIOS_BACK[@]}"
	esperar_backend

	if [[ -n "$RESTAURAR_BASE" ]]; then
		paso "Restaurar la base y los ficheros del respaldo $RESPALDO"
		: "${SGC_DB_ROOT_USER:?para restaurar la base hace falta SGC_DB_ROOT_USER}"
		: "${SGC_DB_ROOT_PASSWORD:?para restaurar la base hace falta SGC_DB_ROOT_PASSWORD}"
		local sql="" pub="" priv="" destino="/home/frappe/frappe-bench/sites/$SITIO/private/backups"
		for f in "$RESPALDO"/*; do
			case "$f" in
			*-database.sql.gz) sql="$f" ;;
			*-private-files.tar) priv="$f" ;;
			*-files.tar) pub="$f" ;;
			esac
		done
		[[ -n "$sql" ]] || die "no hay volcado de la base en $RESPALDO"
		for f in "$sql" "$pub" "$priv"; do
			[[ -n "$f" ]] && docker cp "$f" "$(contenedor backend):$destino/"
		done
		local args=("$destino/$(basename "$sql")" --force
			--db-root-username "$SGC_DB_ROOT_USER" --db-root-password "$SGC_DB_ROOT_PASSWORD")
		[[ -n "$pub" ]] && args+=(--with-public-files "$destino/$(basename "$pub")")
		[[ -n "$priv" ]] && args+=(--with-private-files "$destino/$(basename "$priv")")
		bench restore "${args[@]}"
		# Restaurar trae el site_config del respaldo, que ya estaba en mantenimiento.
	fi

	bench clear-cache
	bench migrate
	bench clear-cache
	"${COMPOSE[@]}" up -d --no-deps "$SERVICIO_FRONT"

	paso "Comprobación"
	# Una imagen anterior a la 1.0.0 no sabe decir su versión: entonces solo cuenta la verificación.
	if comprobar "$ANTERIOR"; then
		mantenimiento off
		echo "✓ $SITIO de vuelta en $ANTERIOR."
	else
		echo "⚠ De vuelta en $ANTERIOR, pero la comprobación no pasa: el sitio sigue en mantenimiento."
		echo "  Si es una versión anterior a la 1.0.0 (sin sgc.estado), mira solo la imagen de cada"
		echo "  servicio y la verificación de arriba, y si no hay bloqueantes quita el mantenimiento:"
		echo "    docker exec <backend> bench --site $SITIO set-maintenance-mode off"
		exit 1
	fi
}

case "$ACCION" in
actualizar) actualizar ;;
comprobar) comprobar "$IMAGEN" ;;
volver) volver ;;
esac
