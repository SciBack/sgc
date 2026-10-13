# Publicación de la imagen

La imagen que se despliega en una instancia la construye y la publica el CI a partir de un tag
de versión. Desde la 1.0.0 ya no se construye a mano encima de la imagen que estaba en
producción.

## Qué se publica

`ghcr.io/sciback/sgc-frappe:<versión>`, por ejemplo `ghcr.io/sciback/sgc-frappe:1.0.0`, y la
misma imagen como `sha-<commit corto>`. Solo **ARM64**, la arquitectura del parque donde corre.
No se publica `latest`: una instancia despliega siempre una versión concreta.

Cada imagen lleva su procedencia en las etiquetas OCI:

| Etiqueta | Valor |
|---|---|
| `org.opencontainers.image.version` | la versión de `sgc/__init__.py` |
| `org.opencontainers.image.revision` | el commit del que salió |
| `org.opencontainers.image.created` | la fecha de ese commit (no la de construcción) |
| `pe.sciback.sgc.frappe` | la versión de Frappe (`deploy/frappe.version`) |
| `pe.sciback.sgc.frappe-docker` | el commit de frappe_docker usado |

```bash
docker image inspect ghcr.io/sciback/sgc-frappe:1.0.0 --format '{{json .Config.Labels}}'
```

Una vez desplegada, la instancia dice la misma versión en `sgc.estado.instancia` (#53).

## Cómo se publica

1. Preparar la versión como dice [`versionado.md`](versionado.md) y mergearla a `main`.
2. Subir el tag sobre ese commit: `git tag v1.0.0 && git push origin v1.0.0`.

El tag dispara `.github/workflows/release.yml`:

| Paso | Qué hace | Si falla |
|---|---|---|
| Coherencia | El tag, `__version__` y el CHANGELOG coinciden | No se construye nada |
| Suite completa | La misma de `tests.yml` | No se publica |
| Construcción | `deploy/construir_imagen.sh`, desde cero, en un runner ARM64 | No se publica |
| Etiquetas | Versión y commit presentes en la imagen | No se publica |
| Prueba de humo | `deploy/smoke_imagen.sh`: sitio nuevo, migrate y versión | No se publica |
| Publicación | Push a `ghcr.io` | — |

Una PR que toque la receta (`Dockerfile.overlay`, los scripts, `imagen.env`, `frappe.version`
o el propio workflow) corre todo menos la publicación.

## Qué fija la imagen

Todo lo que entra está en el repositorio:

- **`deploy/imagen.env`**: commit de frappe_docker, Debian (`bookworm`), Python (`3.14.7`), Node (`24`).
- **`deploy/frappe.version`**: la versión de Frappe.
- **El checkout**: el código del SGC, que `Dockerfile.overlay` copia encima de la base.

Reconstruir el mismo tag produce una imagen **equivalente**: mismas versiones de Frappe, Python,
Node y del SGC, mismas etiquetas. No es idéntica byte a byte, porque los paquetes de Debian y las
dependencias de Python y Node que no van fijadas se resuelven al construir. Por eso un tag
publicado **no se reconstruye en silencio**: si hace falta otra imagen, sale otra versión.

## Construir a mano

Para ensayar una receta antes de abrir la PR, en una máquina ARM64 con Docker:

```bash
deploy/construir_imagen.sh main sgc-frappe:prueba
deploy/smoke_imagen.sh sgc-frappe:prueba "$(sed -n 's/^__version__ = "\(.*\)"$/\1/p' sgc/__init__.py)"
```

El primer argumento es la rama o el tag de `SciBack/sgc` con que se instala la app en la base.
El código que acaba en la imagen es siempre el del checkout.

## Lo que esto no hace

- **No despliega.** Publicar y desplegar son decisiones distintas, y desplegar le corresponde a
  quien opera la instancia: [`docs/despliegue/actualizacion.md`](../despliegue/actualizacion.md).
- **No firma la imagen.** Es deseable y va aparte.
