#!/usr/bin/env bash
# Ensayo con datos ficticios: red interna nueva, sin puertos y sin volúmenes de producción.
# Uso: bash deploy/rehearse_migration.sh IMAGEN_BASE IMAGEN_CANDIDATA ID_ENSAYO
set -euo pipefail
BASE_IMAGE="${1:?Indicar imagen base}"
CANDIDATE_IMAGE="${2:?Indicar imagen candidata}"
RUN_ID="${3:?Indicar identificador único del ensayo}"
[[ "$RUN_ID" =~ ^[a-z0-9-]{4,40}$ ]] || { echo 'ID de ensayo inválido'; exit 2; }
PREFIX="sgc-rehearsal-$RUN_ID"
SITE='migration-test.localhost'
WORKDIR="$(mktemp -d)"
chmod 700 "$WORKDIR"
for name in "$PREFIX-pg" "$PREFIX-redis" "$PREFIX-sites" "$PREFIX-app"; do
  if docker container inspect "$name" >/dev/null 2>&1 || docker volume inspect "$name" >/dev/null 2>&1; then
    echo 'El identificador ya tiene recursos; usar uno nuevo'; exit 2
  fi
done
if docker network inspect "$PREFIX" >/dev/null 2>&1; then echo 'Red de ensayo existente'; exit 2; fi
docker image inspect "$BASE_IMAGE" "$CANDIDATE_IMAGE" >/dev/null
cleanup() {
  docker rm -fv "$PREFIX-app" "$PREFIX-pg" "$PREFIX-redis" >/dev/null 2>&1 || true
  docker volume rm "$PREFIX-sites" >/dev/null 2>&1 || true
  docker network rm "$PREFIX" >/dev/null 2>&1 || true
  rm -rf "$WORKDIR"
}
trap cleanup EXIT
umask 077
python3 - "$WORKDIR/env" <<'PY'
import secrets, sys
with open(sys.argv[1], 'w') as f:
    f.write('POSTGRES_PASSWORD=' + secrets.token_hex(24) + '\n')
    f.write('TEST_ADMIN_PASSWORD=' + secrets.token_hex(24) + '\n')
PY
docker network create --internal "$PREFIX" >/dev/null
docker volume create "$PREFIX-sites" >/dev/null
docker run -d --name "$PREFIX-pg" --network "$PREFIX" --network-alias pg --memory 512m --cpus 1 --env-file "$WORKDIR/env" postgres:16.14 >/dev/null
docker run -d --name "$PREFIX-redis" --network "$PREFIX" --network-alias redis --memory 128m --cpus 0.5 redis:7-alpine >/dev/null
ready=0
for attempt in $(seq 1 30); do
  if docker exec "$PREFIX-pg" pg_isready -U postgres >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
test "$ready" = 1 || { echo 'PostgreSQL de ensayo no inició'; exit 1; }
app() {
  local image="$1"; shift
  docker run --rm -i --name "$PREFIX-app" --network "$PREFIX" --memory 2g --cpus 1 --env-file "$WORKDIR/env" -v "$PREFIX-sites:/home/frappe/frappe-bench/sites" -w /home/frappe/frappe-bench --entrypoint bash "$image" "$@"
}
app "$BASE_IMAGE" -s <<'SH'
set -euo pipefail
bench set-config -g redis_cache redis://redis:6379/0
bench set-config -g redis_queue redis://redis:6379/1
bench set-config -g redis_socketio redis://redis:6379/2
bench new-site migration-test.localhost --db-type postgres --db-host pg --db-port 5432 --db-name readiness --db-root-username postgres --db-root-password "$POSTGRES_PASSWORD" --admin-password "$TEST_ADMIN_PASSWORD" --install-app sgc
cd sites
../env/bin/python <<'PY'
import frappe
frappe.init(site='migration-test.localhost',sites_path='/home/frappe/frappe-bench/sites'); frappe.connect(); frappe.set_user('Administrator')
try:
    assert not frappe.db.exists('DocType', 'Lote Ingesta'), 'La base ya tiene ingesta: no es un ensayo de upgrade'
    indicador=frappe.get_doc({'doctype':'Indicador','codigo':'TEST-MIGRATION-IND','nombre':'Indicador ficticio de migración'}).insert()
    vi=frappe.get_doc({'doctype':'Valor Indicador','indicador':indicador.name,'fuente':'test-migration','valor_num':7.25}).insert()
    frappe.db.commit()
    print('BASELINE: medición ficticia guardada')
finally: frappe.destroy()
PY
SH
docker exec "$PREFIX-pg" pg_dump -U postgres -Fc readiness > "$WORKDIR/baseline.dump"
app "$CANDIDATE_IMAGE" -s <<'SH'
set -euo pipefail
bench --site migration-test.localhost migrate
cd sites
../env/bin/python <<'PY'
import frappe
frappe.init(site='migration-test.localhost',sites_path='/home/frappe/frappe-bench/sites'); frappe.connect()
try:
    for dt in ('Fuente Dato','Regla Validacion','Alerta Indicador','Tablero Indicadores','Lote Ingesta'):
        assert frappe.db.exists('DocType',dt), dt
    rows=frappe.get_all('Valor Indicador',filters={'fuente':'test-migration'},fields=['valor_num','ingesta_clave'])
    assert len(rows)==1 and rows[0].valor_num==7.25 and not rows[0].ingesta_clave
    assert frappe.db.count('Lote Ingesta')==0
    print('MIGRACION: cinco DocTypes presentes; medición heredada intacta; sin adopción silenciosa')
finally: frappe.destroy()
PY
SH
# Restauración completa del DB efímero, no solo limpieza de tablas conocidas.
DB_OWNER="$(docker exec "$PREFIX-pg" psql -U postgres -Atc "SELECT pg_get_userbyid(datdba) FROM pg_database WHERE datname='readiness'")"
test -n "$DB_OWNER"
docker exec "$PREFIX-pg" dropdb -U postgres readiness
docker exec "$PREFIX-pg" createdb -U postgres -O "$DB_OWNER" readiness
docker exec -i "$PREFIX-pg" pg_restore -U postgres -d readiness < "$WORKDIR/baseline.dump"
app "$BASE_IMAGE" -s <<'SH'
set -euo pipefail
cd sites
../env/bin/python <<'PY'
import frappe
frappe.init(site='migration-test.localhost',sites_path='/home/frappe/frappe-bench/sites'); frappe.connect()
try:
    assert not frappe.db.exists('DocType','Lote Ingesta')
    rows=frappe.get_all('Valor Indicador',filters={'fuente':'test-migration'},pluck='valor_num')
    assert rows==[7.25]
    print('ROLLBACK: base restaurada y legible con imagen anterior')
finally: frappe.destroy()
PY
SH
echo "ENSAYO OK: $RUN_ID (datos ficticios; no sustituye restauración integral de producción)"
