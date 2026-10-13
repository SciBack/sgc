#!/usr/bin/env bash
# Construye la imagen desplegable del SGC desde cero (#54).
#
# Hasta la 1.0.0 cada imagen se construía ENCIMA de la que corría en producción: no se podía
# reproducir desde el repositorio y cada despliegue le añadía capas. Aquí se parte de cero y
# todo lo que entra está fijado en el repositorio:
#
#   deploy/imagen.env      frappe_docker (commit), Debian, Python, Node
#   deploy/frappe.version  la versión de Frappe
#   el checkout actual     el código del SGC
#
# Dos pasos:
#   1. Base: Containerfile «custom» de frappe_docker con Frappe y la app sgc instalada.
#   2. Dockerfile.overlay sobre esa base: el código de ESTE checkout, el cliente PostgreSQL 16
#      y la comprobación del mapping de assets. Es el mismo overlay de siempre.
#
# Uso:  deploy/construir_imagen.sh <ref-de-sgc> <imagen:tag>
#       deploy/construir_imagen.sh v1.0.0 ghcr.io/sciback/sgc-frappe:1.0.0
#
# <ref-de-sgc> es el tag o la rama de SciBack/sgc con que se instala la app en la base (bench
# solo acepta ramas o tags, no un commit). El código que acaba en la imagen es siempre el del
# checkout, que el overlay copia encima: la base solo aporta el paquete instalado.
set -euo pipefail

RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
REF="${1:?uso: construir_imagen.sh <ref-de-sgc> <imagen:tag>}"
IMAGEN="${2:?uso: construir_imagen.sh <ref-de-sgc> <imagen:tag>}"

# shellcheck source=/dev/null
. "$RAIZ/deploy/imagen.env"
FRAPPE_BRANCH="$(tr -d '[:space:]' <"$RAIZ/deploy/frappe.version")"
VERSION="$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' "$RAIZ/sgc/__init__.py")"
REVISION="$(git -C "$RAIZ" rev-parse HEAD)"
# La fecha del commit y no la de la construcción: dos construcciones del mismo tag llevan la misma.
CREADA="$(git -C "$RAIZ" log -1 --format=%cI HEAD)"
BASE="sgc-frappe-base:${REVISION:0:12}"

TRABAJO="$(mktemp -d)"
trap 'rm -rf "$TRABAJO"' EXIT

echo "==> frappe_docker @ $FRAPPE_DOCKER_REF"
git init -q "$TRABAJO/frappe_docker"
git -C "$TRABAJO/frappe_docker" fetch -q --depth 1 https://github.com/frappe/frappe_docker "$FRAPPE_DOCKER_REF"
git -C "$TRABAJO/frappe_docker" checkout -q FETCH_HEAD

printf '[{"url": "%s", "branch": "%s"}]\n' "$SGC_REPO" "$REF" >"$TRABAJO/apps.json"

echo "==> Base: Frappe $FRAPPE_BRANCH, Python $PYTHON_VERSION ($DEBIAN_BASE), Node $NODE_VERSION, sgc @ $REF"
DOCKER_BUILDKIT=1 docker build \
	--file "$TRABAJO/frappe_docker/images/custom/Containerfile" \
	--build-arg PYTHON_VERSION="$PYTHON_VERSION" \
	--build-arg DEBIAN_BASE="$DEBIAN_BASE" \
	--build-arg NODE_VERSION="$NODE_VERSION" \
	--build-arg FRAPPE_PATH=https://github.com/frappe/frappe \
	--build-arg FRAPPE_BRANCH="$FRAPPE_BRANCH" \
	--secret id=apps_json,src="$TRABAJO/apps.json" \
	--tag "$BASE" \
	"$TRABAJO/frappe_docker"

echo "==> Imagen: sgc $VERSION ($REVISION) -> $IMAGEN"
DOCKER_BUILDKIT=1 docker build \
	--file "$RAIZ/deploy/Dockerfile.overlay" \
	--build-arg BASE_IMAGE="$BASE" \
	--label org.opencontainers.image.title="sgc-frappe" \
	--label org.opencontainers.image.description="Sistema de Gestión de la Calidad (SciBack) sobre Frappe" \
	--label org.opencontainers.image.source="$SGC_REPO" \
	--label org.opencontainers.image.licenses="MIT" \
	--label org.opencontainers.image.version="$VERSION" \
	--label org.opencontainers.image.revision="$REVISION" \
	--label org.opencontainers.image.created="$CREADA" \
	--label pe.sciback.sgc.frappe="$FRAPPE_BRANCH" \
	--label pe.sciback.sgc.frappe-docker="$FRAPPE_DOCKER_REF" \
	--tag "$IMAGEN" \
	"$RAIZ"

echo "OK -> $IMAGEN (sgc $VERSION, Frappe $FRAPPE_BRANCH)"
