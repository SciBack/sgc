# Entorno local del SGC (lab `frappe-sgc`)

> El README de `~/proyectos/labs/frappe-sgc` remite a este documento diciendo que
> «no hay nada ahí que no esté descrito aquí». **No era cierto: este fichero no
> existía** — se perdió en una reestructuración de `docs/`. Escrito el 13-sep-2026
> reconstruyendo el procedimiento desde el lab en marcha, para que la afirmación
> del README vuelva a ser verdad.

Frappe 16 + PostgreSQL 16 + Redis sobre OrbStack, ARM64 (M1). Sirve para probar lo
que **no se puede probar en producción**: publicar documentos, recorrer workflows,
sembrar datos y medir permisos con usuarios de verdad.

## Lo que hay

| | |
|---|---|
| Carpeta | `~/proyectos/labs/frappe-sgc` |
| Proyecto compose | `sgc-test` |
| Frontend | `http://localhost:8088` |
| Sitios | `calidad.localhost` (el bueno) · `fabrica.localhost` |
| Imagen | `sgc-nativo:v16*`, construida en local |
| Overrides propios | `arm64.yaml` (M1) · `pg16.yaml` (PostgreSQL **16.14**, igual que producción; el override oficial trae 15) |

## Arrancar y parar

```bash
cd ~/proyectos/labs/frappe-sgc/frappe_docker
docker compose --project-name sgc-test start     # o stop
docker compose --project-name sgc-test ps
```

⚠️ **`start` no levanta lo que esté caído.** El 13-sep el contenedor `sgc-test-db-1`
llevaba **dos días parado** con el resto en marcha: el frontend respondía y toda
consulta fallaba con `could not translate host name "db"`. Si algo no conecta,
mirar `docker ps -a` antes de sospechar del código.

## Reconstruir la imagen

El código de la app **va dentro de la imagen** — no hay bind mount al repo. Así que
cualquier cambio en `sgc/` exige reconstruir, o el lab mide código antiguo.

```bash
cd ~/proyectos/labs/frappe-sgc
# apps.json apunta por defecto a main; para probar una rama, cámbiala aquí
export APPS_JSON_BASE64=$(base64 < apps.json | tr -d '\n')

cd frappe_docker
docker build \
  --build-arg=FRAPPE_PATH=https://github.com/frappe/frappe \
  --build-arg=FRAPPE_BRANCH=version-16 \
  --build-arg=APPS_JSON_BASE64="$APPS_JSON_BASE64" \
  --build-arg=CACHE_BUST="$(date +%s)" \
  --platform=linux/arm64 \
  --tag=sgc-nativo:v16 \
  --file=images/custom/Containerfile .
```

`CACHE_BUST` es necesario: sin él Docker reutiliza la capa del `git clone` y
reconstruye con el código de la vez anterior — el fallo más fácil de no ver.

**Respaldar antes de recrear contenedores** (ver más abajo por qué `bench backup`
no sirve aquí):

```bash
docker exec -e PGPASSWORD=<pass> sgc-test-db-1 \
  pg_dump -U <db> -d <db> -Fc > lab-calidad-$(date +%Y%m%d-%H%M).dump
```

Credenciales en `sites/calidad.localhost/site_config.json` dentro del contenedor.

## Cuatro trampas verificadas (13-sep-2026)

Todas costaron tiempo real y ninguna es evidente.

### 1. Copiar código al contenedor no recarga el proceso web

Gunicorn conserva los módulos en memoria. Un script lanzado con el python del bench
ve el código nuevo **y la API HTTP sigue sirviendo el viejo**, con `ImportError` de
módulos que sí están en disco. `bench clear-cache` **no** sirve:

```bash
docker restart sgc-test-backend-1     # esto sí
```

Un `restart` conserva los ficheros copiados a mano; **recrear** el contenedor los
pierde y vuelve al código de la imagen.

### 2. El site no se elige con la cabecera `Host`

El frontend fuerza `FRAPPE_SITE_NAME_HEADER=fabrica.localhost`, así que todo lo que
entre por `:8088` va a ese site y da **401** con credenciales de `calidad.localhost`.
Hay que ir al backend (`:8000`) indicando el site:

```
X-Frappe-Site-Name: calidad.localhost
```

**No `Host`.** Con `curl` la `Host` funciona y por eso se escribe sola; **desde
código no**: es un *forbidden header name* de la spec de `fetch`, el runtime la
descarta en silencio y Frappe responde un 404 en HTML que no explica nada.

### 3. `bench backup` falla — y es el mismo fallo que producción

```
pg_dump: error: aborting because of server version mismatch
server version: 16.14 · pg_dump version: 15.19
```

La imagen trae cliente 15 y el servidor es 16.14. **Es exactamente el fallo que
bloqueó el respaldo de producción**, así que el lab sirve para reproducirlo. La
salida es volcar desde el contenedor de Postgres, que sí tiene cliente 16 (comando
arriba). Una imagen reconstruida con base actual incorpora cliente 16.

### 4. `bench console` miente al cargar datos

Procesa línea a línea: un `for` con `try`/`continue` revienta con
`SyntaxError: 'continue' not properly in loop`, imprime «0 creados» y **no falla**.
Cargar datos siempre como **fichero**:

```bash
docker cp script.py sgc-test-backend-1:/tmp/script.py
docker exec sgc-test-backend-1 bash -lc \
  'cd /home/frappe/frappe-bench/sites && ../env/bin/python /tmp/script.py'
```

## Sembrar datos

`sembrar_lab.py` (en `instituciones/upeu/sgc-frontend/docs/`) deja el lab con una
rama publicada coherente: procesos `Vigente`, fichas y procedimientos `Publicado`
con BPMN adjunto, un documento recorrido por su **workflow real** con tres usuarios
distintos, y el usuario de solo lectura del portal. Es idempotente.

Dos cosas que aprendió ese script y conviene no repetir:

- **`db.set_value` no dispara `on_update`.** Publicar así deja el estado cambiado y
  los derivados sin generar (el PDF de la ficha, por ejemplo). Para que el ciclo
  real ocurra, `doc.save()`.
- **El rol del portal necesita `desk_access=0`**, y en ese orden: mientras el rol
  tenga desk access, poner el usuario como `Website User` **revierte en silencio** y
  te quedas con un System User que puede listar `User` entero.

## Diferencias con producción que hay que vigilar

El lab **diverge**, y creerlo idéntico lleva a conclusiones falsas. El 13-sep cinco
de sus seis fichas no pasaban su propia validación porque sus indicadores tenían
`marco_normativo` — y **producción no tenía ese problema**. Antes de dar por bueno
un hallazgo del lab que suene a bug de producción, comprobarlo contra producción por
API (solo lectura).

## ⚠️ El clon interno bajo `development/`

Ha tenido un PAT de GitHub en texto plano en su `git remote`. **No hacer `git
pull`/`push` desde ahí.** Sincronizar por `rsync` desde el canónico.
