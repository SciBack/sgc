# Versión de Frappe — fijada, no flotante

**Fuente de verdad:** `deploy/frappe.version` (una línea, un tag de git de Frappe).

## Por qué está fijada
La versión de Frappe **no debe** tomarse de la rama móvil `version-16`: cada build
agarraría un commit distinto y prod/CI/lab derivarían solos (ya pasó: prod 16.27.0,
CI 16.31.0, lab 16.32.0 sin que nadie lo pidiera). Se fija a un **tag concreto** para
que los tres entornos corran exactamente la misma.

## Política: siempre la última, pero a propósito
Mantenerse en la última release de Frappe v16 es el objetivo — pero actualizando
**conscientemente**, no por deriva. Para subir de versión:

1. Ver la última tag:  `git ls-remote --tags --refs https://github.com/frappe/frappe | grep -oE 'v16\.[0-9]+\.[0-9]+$' | sort -V | tail -1`
2. Escribir esa tag en `deploy/frappe.version`.
3. Actualizarla también en `.github/workflows/tests.yml` (`--frappe-branch <tag>`).
4. Reconstruir imágenes con `--build-arg FRAPPE_BRANCH=<tag>` (lab y base de prod).
5. Correr la suite; si verde, desplegar.

Así "siempre la última" es una decisión revisada, reproducible y reversible.

## Cliente PostgreSQL para backups

`Dockerfile.overlay` conserva `BASE_IMAGE` obligatorio y exige Debian 12 bookworm.
Instala **solo `postgresql-client-16`**, sin servidor, desde el
[repositorio oficial PGDG](https://www.postgresql.org/download/linux/debian/)
mediante HTTPS y clave limitada por `Signed-By`. Bookworm y arm64 están soportados.
El PATH antepone `/usr/lib/postgresql/16/bin`; el build verifica la ruta y el major
16 de `pg_dump`, `pg_restore` y `psql`. La caché APT se elimina en la misma capa.

Esto corrige la incompatibilidad del cliente 15 heredado con el servidor 16:
[pg_dump no acepta un servidor de major más nuevo](https://www.postgresql.org/docs/16/app-pgdump.html).
No modifica el servidor de base de datos. Se conserva el cliente anterior instalado
por la base, pero deja de ser el seleccionado por PATH.

Riesgos de construcción: disponibilidad de PGDG/DNS/TLS/clave y cambios de paquetes
APT. El major queda fijado a 16; la revisión menor y dependencias se resuelven al
construir y no son reproducibles byte por byte. Registrar el digest de la imagen y
la versión instalada para cada release; no reconstruir un tag aprobado en silencio.

Antes de activar una imagen construida, comprobar los tres binarios también como
usuario `frappe`, ejecutar `bench --site <sitio-pruebas> backup --with-files` contra
PostgreSQL 16 en un sitio aislado y verificar el gzip SQL, los tar y una restauración
de prueba. Los asserts de versión no sustituyen esa prueba de backup/restauración.
