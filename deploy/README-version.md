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
