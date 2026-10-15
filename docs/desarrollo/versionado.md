# Versionado del SGC

El SGC usa **versionado semántico** (`MAYOR.MENOR.PARCHE`). En una librería, lo que rompe a
quien la usa es su API. En este producto lo que rompe a una institución es **el modelo de datos
y los flujos de trabajo**, y de ahí sale el criterio.

## Qué sube cada número

| Sube | Cuándo | Ejemplos |
|---|---|---|
| **MAYOR** | Cambia el modelo de datos de forma que exige una migración con decisiones, o desaparece un flujo, un DocType o un campo que alguien usaba. | Fusionar dos DocTypes; retirar un estado de un workflow; cambiar la clave de un DocType. |
| **MENOR** | DocType, campo, informe, flujo o paso de despliegue **nuevo**, compatible con lo anterior. La migración lo aplica sola. | Un informe nuevo; un campo opcional; un paso más en `f_deploy_run_all`. |
| **PARCHE** | Corrección **sin cambio de esquema**: no añade ni quita campos ni estados. | Un cálculo que daba mal; un permiso que faltaba en la matriz; un texto. |

Ante la duda entre dos, se elige la mayor. Una versión no se reutiliza ni se mueve: si un tag
publicado sale mal, se corrige con la siguiente.

## Dónde vive la versión

- **`sgc/__init__.py`** (`__version__`): la única fuente. `pyproject.toml` la lee de ahí, Frappe
  la registra en cada `migrate` (`Installed Applications`) y el endpoint de estado la devuelve.
- **El tag de git** `vX.Y.Z`: marca la publicación y dispara la construcción de la imagen.
- **`CHANGELOG.md`**: una entrada `## [X.Y.Z] - AAAA-MM-DD` por versión publicada.

Las tres tienen que coincidir. `deploy/check_version.py` lo comprueba: en cada PR (versión
válida y con entrada en el CHANGELOG) y al publicar un tag (además, que el tag coincida). Si no
coinciden, la publicación falla.

## El manual de usuario va con la versión

El manual (`docs-site/`) vive en este mismo repo, así que el manual del tag `vX.Y.Z` **es** el
manual del SGC X.Y.Z. Su título lo lee de `sgc/__init__.py`: «Manual del SGC X.Y.Z».

- Un cambio que altera lo que ve el usuario corrige su página del manual **en la misma PR**.
- Cada institución publica el manual del **mismo tag** que corre en su producción. En el overlay
  de despliegue el tag se fija en un solo sitio y la publicación se niega si no coincide con la
  versión de la imagen en marcha.
- Las versiones anteriores del manual quedan en sus tags; no hay selector de versiones porque
  cada institución usa una sola.

## Cómo se escribe el CHANGELOG

Para la persona de calidad o de sistemas que lo lee, no para quien programa:

- ✅ «La evidencia de cierre es obligatoria al verificar una acción de mejora».
- ❌ «refactor de accion_mejora.py».

Cada entrada dice si **requiere migrar**. Si una versión exige además un paso manual (declarar
una clave en `site_config`, revisar permisos antes de migrar, etc.), se escribe en la entrada:
quien actualiza no tiene por qué leer el código.

Lo que se va haciendo entre versiones se apunta bajo `## [Sin publicar]`. Al publicar, ese
bloque pasa a ser la entrada de la versión con su fecha.

## Publicar una versión

1. Mover lo de `[Sin publicar]` a una entrada `## [X.Y.Z] - AAAA-MM-DD`.
2. Poner `__version__ = "X.Y.Z"` en `sgc/__init__.py`.
3. Comprobar en local: `python deploy/check_version.py --tag vX.Y.Z`.
4. Merge a `main` por PR, como cualquier cambio.
5. Crear el tag sobre ese commit de `main` y subirlo: `git tag vX.Y.Z && git push origin vX.Y.Z`.

El tag dispara `.github/workflows/release.yml`, que vuelve a comprobar la coherencia antes de
publicar nada.
