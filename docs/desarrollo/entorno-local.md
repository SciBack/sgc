# Entorno de desarrollo local

Cómo levantar el SGC en tu propia máquina para desarrollar, probar cambios y
abrir un Pull Request. El resultado es un Frappe 16 completo con PostgreSQL,
Redis y la app `sgc` instalada, aislado de producción.

> **Producción no se toca desde aquí.** Este entorno es solo para desarrollo:
> no tiene datos reales, no se expone a internet y nadie debe trabajar en él
> como si fuera el sistema institucional.

## Antes de empezar

| Requisito | Detalle |
|---|---|
| Docker | Con el plugin `compose` (v2). `docker compose version` debe responder |
| git | Cualquier versión reciente |
| Disco | ~10 GB libres — la imagen ronda los 4-5 GB |
| RAM | 4 GB disponibles para los contenedores |
| Arquitectura | **x86_64** (camino principal) o **ARM64** (ver más abajo) |

Comprueba tu arquitectura antes de nada, porque decide un paso:

```bash
uname -m     # x86_64  -> camino normal
             # aarch64 / arm64 -> ver "Si tu máquina es ARM64"
```

## 1. Preparar el directorio de trabajo

`frappe_docker` es el proyecto oficial de Frappe con los `compose` y los
`Containerfile`. No es parte de este repositorio: se clona aparte.

```bash
mkdir -p ~/labs/frappe-sgc && cd ~/labs/frappe-sgc
git clone --depth 1 https://github.com/frappe/frappe_docker.git
```

## 2. Declarar qué apps van dentro de la imagen

```bash
cat > apps.json <<'EOF'
[
  {"url": "https://github.com/SciBack/sgc", "branch": "main"}
]
EOF
```

Dos cosas que se equivocan a menudo:

- **`frappe` no se pone aquí.** El framework ya viene en la imagen base; si lo
  añades, se instala dos veces y el build falla.
- **La rama de la app `sgc` es `main`.** No existe ninguna rama `version-16` en
  este repositorio — ese nombre pertenece a la rama del *framework* Frappe, que
  es otra cosa y se pasa aparte en el paso siguiente.

## 3. Construir la imagen

El build clona la app desde GitHub dentro de la imagen. El `apps.json` se pasa
como **secret de BuildKit**, no como argumento: así no queda escrito en ninguna
capa de la imagen.

```bash
cd ~/labs/frappe-sgc/frappe_docker
docker build \
  --secret id=apps_json,src=../apps.json \
  --build-arg FRAPPE_BRANCH=version-16 \
  --tag sgc-dev:v16 \
  --file images/layered/Containerfile .
```

Aquí sí `FRAPPE_BRANCH=version-16`: es la rama del **framework Frappe**, no la
de la app. Tarda entre 10 y 20 minutos la primera vez.

Si el build falla al clonar la app, comprueba que la URL de `apps.json` es
accesible sin credenciales — el repositorio es público, así que no hace falta
token de GitHub. **Nunca metas un token en la URL del `apps.json`**: quedaría
grabado en la imagen.

## 4. Configurar el entorno

```bash
cd ~/labs/frappe-sgc/frappe_docker
cp example.env .env
```

Edita `.env` y deja estas claves con estos valores:

```ini
CUSTOM_IMAGE=sgc-dev
CUSTOM_TAG=v16
PULL_POLICY=never
DB_PASSWORD=<elige una contraseña para tu Postgres local>
FRAPPE_SITE_NAME_HEADER=calidad.localhost
HTTP_PUBLISH_PORT=8088
UPSTREAM_REAL_IP_ADDRESS=127.0.0.1
```

`PULL_POLICY=never` es importante: la imagen la acabas de construir en local y
no existe en ningún registry, así que Docker no debe intentar descargarla.

Si el puerto 8088 ya está ocupado en tu máquina, cambia `HTTP_PUBLISH_PORT`.

## 5. Alinear PostgreSQL con producción

El SGC usa **PostgreSQL**, no MariaDB (que es el motor por defecto de Frappe).
El override oficial `compose.postgres.yaml` trae PostgreSQL 15, pero producción
corre **16.14**. Para que el entorno se parezca a lo real, se añade un override
propio que solo cambia la imagen:

```bash
cd ~/labs/frappe-sgc
cat > pg16.yaml <<'EOF'
services:
  db:
    image: postgres:16.14
EOF
```

## 6. Levantar

```bash
cd ~/labs/frappe-sgc/frappe_docker
docker compose \
  -f compose.yaml \
  -f overrides/compose.postgres.yaml \
  -f overrides/compose.redis.yaml \
  -f overrides/compose.noproxy.yaml \
  -f ../pg16.yaml \
  --project-name sgc-dev up -d
```

Comprueba que los nueve servicios están arriba (`configurator` sale con
`Exited (0)`: es normal, hace su trabajo y termina):

```bash
docker compose --project-name sgc-dev ps
```

## 7. Crear el sitio e instalar la app

```bash
docker compose --project-name sgc-dev exec backend \
  bench new-site calidad.localhost \
    --db-type postgres \
    --db-host db \
    --no-mariadb-socket \
    --admin-password admin \
    --install-app sgc
```

`--db-type postgres` no es opcional: sin él, `bench` intenta MariaDB y falla.

Abre **http://localhost:8088** y entra con `Administrator` / `admin`.

## 8. Trabajar sobre el código

La app vive dentro del contenedor, en
`/home/frappe/frappe-bench/apps/sgc`. Para desarrollar cómodamente, clona el
repositorio en tu máquina y móntalo sobre esa ruta:

```bash
cd ~/labs/frappe-sgc
git clone https://github.com/SciBack/sgc.git
```

Añade un override que monte tu clon dentro de los contenedores:

```bash
cat > dev-mount.yaml <<'EOF'
services:
  backend:
    volumes:
      - ../sgc:/home/frappe/frappe-bench/apps/sgc
  scheduler:
    volumes:
      - ../sgc:/home/frappe/frappe-bench/apps/sgc
  queue-short:
    volumes:
      - ../sgc:/home/frappe/frappe-bench/apps/sgc
  queue-long:
    volumes:
      - ../sgc:/home/frappe/frappe-bench/apps/sgc
EOF
```

Y vuelve a levantar añadiendo `-f ../dev-mount.yaml` a la orden del paso 6.
A partir de ahí, editas en tu editor y el cambio está dentro al instante.

Tras cambiar un DocType o cualquier fichero `.json`:

```bash
docker compose --project-name sgc-dev exec backend \
  bench --site calidad.localhost migrate
```

Tras cambiar Python, basta con reiniciar el backend:

```bash
docker compose --project-name sgc-dev restart backend
```

## 9. Correr la suite antes de abrir el PR

Los mismos tests que ejecuta el CI:

```bash
docker compose --project-name sgc-dev exec backend \
  bench --site calidad.localhost run-tests --app sgc
```

Que pasen en local antes de subir ahorra un ciclo entero de CI.

## Si tu máquina es ARM64

En Apple Silicon (M1/M2/M3/M4) o en un servidor Graviton, el build produce
imágenes ARM64 de forma natural, pero el `compose` de Frappe puede intentar
resolver alguna imagen a `linux/amd64`. Se corrige con un override que fija la
plataforma en los siete servicios:

```bash
cd ~/labs/frappe-sgc
cat > arm64.yaml <<'EOF'
services:
  configurator:
    platform: linux/arm64
  backend:
    platform: linux/arm64
  frontend:
    platform: linux/arm64
  websocket:
    platform: linux/arm64
  queue-short:
    platform: linux/arm64
  queue-long:
    platform: linux/arm64
  scheduler:
    platform: linux/arm64
EOF
```

Añade `-f ../arm64.yaml` a la orden del paso 6. Todo lo demás es idéntico.

En x86_64 **no** uses este override: forzaría emulación y el entorno se
arrastraría.

## Flujo de contribución

```
rama → commits → push → Pull Request → CI verde → revisión → merge a main
```

1. **Una rama por cambio**, nombrada por su naturaleza: `feat/…`, `fix/…`,
   `docs/…`.
2. **Abre el PR contra `main`.** La rama `main` está protegida: no se puede
   empujar directamente, ni forzar, ni borrar.
3. **El CI se ejecuta solo.** El check `Integración (PostgreSQL)` levanta un
   Frappe completo con PostgreSQL y corre la suite. Tiene que quedar en verde.
4. **Hace falta una aprobación** antes de poder mergear. Si empujas más commits
   después de aprobado, la aprobación caduca y hay que revisar de nuevo.
5. **Las conversaciones del PR deben quedar resueltas** para poder mergear.

### Qué NO puede entrar en este repositorio

`SciBack/sgc` es un repositorio **público**. No debe entrar aquí, ni en el
código, ni en los tests, ni en los mensajes de commit, ni en las descripciones
de los PR:

- Datos personales: nombres, DNI, correos institucionales, teléfonos.
- Documentos internos de la institución.
- Contraseñas, tokens, claves de API o cadenas de conexión reales.
- Volcados de base de datos o capturas con datos de personas.

Para los tests, usa datos inventados. Si necesitas algo institucional real para
probar, se queda en tu máquina y no se commitea.

## Problemas frecuentes

| Síntoma | Causa y arreglo |
|---|---|
| `pull access denied` al levantar | Falta `PULL_POLICY=never` en `.env`, o `CUSTOM_IMAGE`/`CUSTOM_TAG` no coinciden con la etiqueta que construiste |
| `bench new-site` falla hablando de MariaDB | Olvidaste `--db-type postgres` |
| El puerto 8088 no responde | Otro proceso lo ocupa; cambia `HTTP_PUBLISH_PORT` y vuelve a levantar |
| La web carga sin estilos | `docker compose --project-name sgc-dev exec backend bench --site calidad.localhost clear-cache` |
| El build tarda muchísimo o va lentísimo | En x86_64 estás aplicando el override ARM (o al revés): quita el que no toca |
| Un cambio en Python no se refleja | Reinicia el backend; si tocaste un `.json`, hace falta `migrate` |

## Empezar de cero

Borra el entorno entero, volúmenes incluidos, y repite desde el paso 4:

```bash
docker compose --project-name sgc-dev down -v
```
