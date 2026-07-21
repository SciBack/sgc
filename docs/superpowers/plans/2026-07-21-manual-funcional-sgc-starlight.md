# Manual funcional protegido de SGC UPeU Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Construir, verificar y publicar el manual funcional protegido de SGC en `https://calidad.upeu.edu.pe/manual/`, respaldado por el código vigente y sin regresiones en la aplicación.

**Architecture:** `docs-site/` conserva el contenido y la interfaz canónica Astro + Starlight; un endpoint Frappe mínimo autoriza la sesión; el overlay UPeU en `UPeU-Infra/upeu-ops` hornea marca y configuración productiva en una imagen estática independiente. Caddy autentica `/manual/*`, elimina credenciales antes del upstream estático y deja todas las demás rutas en el stack actual.

**Tech Stack:** Frappe v16/Python, Vue 3/Vite, Astro 7, Starlight 0.41, TypeScript/Node 24, Playwright + axe-core, Nginx unprivileged, Docker Compose, Caddy 2.11, GitHub Actions.

---

## Mapa de archivos

### Repositorio canónico `SciBack/sgc`

- `docs-site/src/data/coverage.json`: inventario verificable de roles, workflows y flujos programáticos.
- `docs-site/src/content/docs/`: manual funcional; una página por rol y por flujo.
- `docs-site/src/components/`: componentes MDX pequeños para pasos, resultados, estados y evidencia.
- `docs-site/src/styles/sciback.css`: tokens neutrales y pulido Starlight.
- `docs-site/src/components/Head.astro`: punto de extensión genérico `/manual/institution.css`.
- `docs-site/src/content/docs/404.md`: página 404 propia.
- `docs-site/scripts/`: verificadores de enlaces, cobertura, privacidad, artefacto y canarios.
- `docs-site/tests/`: pruebas Node/Playwright y fixtures negativas.
- `docs-site/astro.config.mjs`: `site`/`base` parametrizados, sitemap y navegación.
- `docs-site/package.json`: comandos de check y verificación.
- `docs-site/Dockerfile`: imagen canónica neutral para CI/local.
- `docs-site/nginx.conf`: 404 real, headers y caché privada.
- `sgc/manual_auth.py`: contrato 204/302 cerrado sobre `frappe.session.user`.
- `sgc/tests/test_manual_auth.py`: sesión válida, Guest y redirección fija.
- `.github/workflows/docs.yml`: validación sin GitHub Pages.
- `.gitignore` y `.dockerignore`: contextos pequeños y artefactos ignorados.

### Overlay cliente `UPeU-Infra/upeu-ops`

- `services/sgc/manual/institution.css`: solo tokens y ajustes de marca UPeU.
- `services/sgc/manual/Dockerfile`: build multi-contexto que hornea manual + overlay.
- `services/sgc/manual/compose.yml`: candidato por release y red externa `sgc-proxy`.
- `services/sgc/caddy/{Caddyfile,docker-compose.yml}`: configuración efectiva versionada de Caddy.
- `services/sgc/manual/scripts/release.sh`: build, candidato saludable, promoción y estado atómico.
- `services/sgc/manual/scripts/smoke.mjs`: matriz HTTP anónima/autenticada sin persistir secretos.
- `services/sgc/manual/tests/`: upstream Frappe simulado y prueba integrada.
- `.github/workflows/sgc-manual.yml`: validación del overlay y build productivo.

## Task 1: Cerrar el inventario funcional desde el código

**Files:**
- Create: `docs-site/src/data/coverage.json`
- Create: `docs-site/scripts/verify-coverage.mjs`
- Create: `docs-site/tests/verify-coverage.test.mjs`
- Create: `docs-site/tests/fixtures/coverage-invalid.json`
- Modify: `docs-site/package.json`

- [ ] **Step 1: Extraer fuentes con `codebase-memory`**

Consultar rutas frontend, menús, los 14 workflows, `f3b_rbac.py`, controladores con validación,
`scoring.py`, `confirmacion.py`, `capa.py`, `tasks.py`, reportes y tests. Guardar en el manifiesto
solo rutas de archivo y símbolos, nunca datos productivos.

- [ ] **Step 2: Crear el manifiesto cerrado**

Formato mínimo:

```json
{
  "roles": [{"id":"dpgc","kind":"role","page":"roles/dpgc.md","sources":["sgc/setup/f3b_rbac.py"],"status":"operativo"}],
  "flows": [{"id":"autoevaluacion","kind":"workflow","page":"flujos/autoevaluacion.md","sources":["sgc/setup/f2_workflow.py"],"status":"operativo"}]
}
```

Incluir los 14 roles y los 14 workflows definidos en la especificación; añadir flujos
programáticos separados para autenticación/navegación, scoring y confirmación, evidencia y
trazabilidad, CAPA, CBC, reportes PDF/Excel, indicadores, gobierno, procesos, obligaciones,
notificaciones y tareas diarias cuando el código confirme acciones independientes.

- [ ] **Step 3: Escribir primero la prueba y el canario de cobertura**

`verify-coverage.test.mjs` importará el módulo aún inexistente y probará esquema, estados
permitidos (`operativo`, `parcial`, `no-ejecutable`), IDs duplicados y fuentes. La fixture tendrá
un ID duplicado, una página ausente y una fuente inexistente.

- [ ] **Step 4: Ejecutar RED**

Run: `cd docs-site && node --test tests/verify-coverage.test.mjs`  
Expected: FAIL con `ERR_MODULE_NOT_FOUND` para `scripts/verify-coverage.mjs`.

- [ ] **Step 5: Implementar el verificador**

Exportar `validateCoverage(manifest, { requirePages })`. El modo `--manifest-only` valida
esquema, IDs, estados y fuentes; el modo completo exige páginas y las 13 secciones obligatorias
de cada flujo mediante frontmatter estructurado.

Agregar en `package.json`: `verify:coverage:manifest` (`--manifest-only`),
`verify:coverage:roles` (`--kind role --require-pages`) y `verify:coverage` (completo).

- [ ] **Step 6: Ejecutar GREEN parcial y canario**

Run: `cd docs-site && npm run verify:coverage:canary`  
Expected: PASS del canario porque `verify-coverage.mjs` rechaza la fixture con exit code 1.

Run: `cd docs-site && npm run verify:coverage:manifest`  
Expected: PASS aunque las páginas aún no existen; esquema, fuentes y 14+14 entradas válidas.

- [ ] **Step 7: Reservar la validación completa**

No ejecutar aún `verify:coverage`; debe fallar hasta que Tasks 4-6 creen y completen las páginas.

- [ ] **Step 8: Commit**

```bash
git add docs-site/src/data/coverage.json docs-site/scripts/verify-coverage.mjs docs-site/tests/verify-coverage.test.mjs docs-site/tests/fixtures/coverage-invalid.json docs-site/package.json
git commit -m "docs: inventaría roles y flujos funcionales del SGC"
```

## Task 2: Proteger el manual con la sesión Frappe

**Files:**
- Create: `sgc/manual_auth.py`
- Create: `sgc/tests/test_manual_auth.py`

- [ ] **Step 1: Escribir pruebas Frappe que fallen**

Cubrir:

```python
def test_authorize_guest_redirects_to_fixed_local_login(): ...
def test_authorize_authenticated_returns_204_without_identity(): ...
def test_expired_session_redirects(): ...
def test_revoked_session_redirects(): ...
def test_auxiliary_user_cookie_does_not_authorize(): ...
def test_response_is_private_no_store(): ...
```

La respuesta Guest debe ser `302` con `Location: /login?redirect-to=/manual/`; autenticada `204`.

- [ ] **Step 2: Ejecutar el módulo y demostrar el fallo**

Run: `bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_manual_auth`  
Expected: FAIL porque `sgc.manual_auth` aún no existe.

- [ ] **Step 3: Implementar el endpoint mínimo**

Usar `@frappe.whitelist(allow_guest=True)`, consultar únicamente `frappe.session.user`, fijar
`Cache-Control: private, no-store`, redirección local constante y `204` sin cuerpo para una sesión
válida. No aceptar `redirect_to` ni devolver usuario/roles.

- [ ] **Step 4: Ejecutar pruebas**

Run: `bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_manual_auth`  
Expected: PASS.

- [ ] **Step 5: Ejecutar suite de seguridad/permissions relacionada**

Run: `bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_permissions`  
Expected: PASS sin cambios de RBAC.

- [ ] **Step 6: Commit**

```bash
git add sgc/manual_auth.py sgc/tests/test_manual_auth.py
git commit -m "feat: autoriza el manual con la sesión Frappe"
```

## Task 3: Reconfigurar Astro/Starlight y el sistema visual neutral

**Files:**
- Modify: `docs-site/astro.config.mjs`
- Modify: `docs-site/src/content.config.ts`
- Create: `docs-site/src/styles/sciback.css`
- Create: `docs-site/src/components/Head.astro`
- Create: `docs-site/public/institution.css`
- Create: `docs-site/src/content/docs/404.md`
- Create: `docs-site/tests/config.test.mjs`
- Create: `docs-site/scripts/verify-links.mjs`
- Create: `docs-site/scripts/verify-privacy.mjs`
- Create: `docs-site/scripts/verify-orphans.mjs`
- Create: `docs-site/tests/verify-links.test.mjs`
- Create: `docs-site/tests/verify-privacy.test.mjs`
- Modify: `docs-site/src/content/docs/index.mdx`
- Modify: `docs-site/package.json`
- Modify: `docs-site/package-lock.json`

- [ ] **Step 1: Añadir test de configuración que falle**

Crear `tests/config.test.mjs` que exija `DOCS_SITE`, use `DOCS_BASE=/manual`, compruebe sitemap y rechace
`sciback.github.io`, enlaces `/sgc/` y `editLink` antiguo.

- [ ] **Step 2: Demostrar el fallo actual**

Run: `cd docs-site && npm run verify:config`  
Expected: FAIL por `site: https://sciback.github.io` y `base: /sgc`.

- [ ] **Step 3: Parametrizar Astro**

Leer `DOCS_SITE`, validar URL HTTPS, normalizar `DOCS_BASE`, configurar `output: 'static'`, sitemap,
búsqueda local y sidebar funcional. Los links se expresan relativos al contenido, no con el base
hardcodeado.

- [ ] **Step 4: Aplicar SciBack neutral y `emil-design-eng`**

Importar los tokens neutrales canónicos; aplicar base 4 px, zonas de 44 px, radios medios, foco
visible, `:active scale(.97)`, transiciones de propiedades concretas <300 ms y
`prefers-reduced-motion`. No introducir azul/ámbar UPeU en esta hoja.

- [ ] **Step 5: Crear el punto de extensión institucional**

`Head.astro` añadirá `<link rel="stylesheet" href={`${base}/institution.css`}>`; el build neutral
incluye un placeholder vacío para que local/CI no produzcan 404.

- [ ] **Step 6: Crear 404 y portada funcional**

La portada enlaza a preparación, recorrido E2E, roles y regresión. `404.md` no redirige.

- [ ] **Step 7: Crear harness temprano de enlaces y privacidad**

Escribir primero tests Node con HTML/Markdown mínimo roto, comprobar RED por módulos ausentes,
implementar parsers y obtener GREEN. `verify-links` revisa páginas/anchors; `verify-privacy`
revisa fuente+dist con allowlist; `verify-orphans` compara sidebar, árbol y coverage. Ninguno
necesita todavía Playwright.

- [ ] **Step 8: Verificar build, tipos y harness**

Run: `cd docs-site && node --test tests/config.test.mjs tests/verify-links.test.mjs tests/verify-privacy.test.mjs && DOCS_SITE=https://manual.invalid DOCS_BASE=/manual npm run check && DOCS_SITE=https://manual.invalid DOCS_BASE=/manual npm run build`  
Expected: PASS; `dist/404.html`, `dist/sitemap-index.xml` y Pagefind presentes.

- [ ] **Step 9: Commit**

```bash
git add docs-site
git commit -m "feat(docs): configura Starlight para el manual protegido"
```

## Task 4: Crear las 14 guías independientes por rol

**Files:**
- Create: `docs-site/src/content/docs/roles/index.md`
- Create: `docs-site/src/content/docs/roles/*.md` (14 páginas declaradas en coverage)
- Create: `docs-site/src/components/RoleCard.astro`
- Create: `docs-site/src/components/PermissionMatrix.astro`

- [ ] **Step 1: Generar la matriz desde `f3b_rbac.py`**

Documentar create/read/write/submit/cancel, permlevel 1 y User Permission. No inferir menús por
rol si la SPA no los filtra; marcar esa diferencia como restricción confirmada.

- [ ] **Step 2: Escribir cada guía con la misma plantilla**

Propósito, inicio de sesión, menús/destinos, tareas, acciones prohibidas, traspaso a otros roles,
cuenta/datos de prueba y limitaciones. `Lector Externo` queda “no ejecutable”; `System Manager`
incluye el `create=0` deliberado en DocTypes de la matriz.

- [ ] **Step 3: Verificar cobertura y enlaces**

Run: `cd docs-site && npm run verify:coverage:roles && npm run verify:links`  
Expected: PASS; 14/14 guías presentes.

- [ ] **Step 4: Commit**

```bash
git add docs-site/src/content/docs/roles docs-site/src/components docs-site/src/data/coverage.json
git commit -m "docs: añade guías funcionales para los 14 roles"
```

## Task 5: Documentar cada workflow y flujo programático

**Files:**
- Create: `docs-site/src/content/docs/flujos/index.md`
- Create: `docs-site/src/content/docs/flujos/*.md`
- Create: `docs-site/src/components/TestStep.astro`
- Create: `docs-site/src/components/StateFlow.astro`
- Create: `docs-site/src/components/ExpectedResult.astro`
- Create: `docs-site/src/components/EvidenceRequired.astro`
- Create: `docs-site/src/components/NegativeCase.astro`

- [ ] **Step 1: Documentar los 14 workflows desde sus specs Python**

Copiar estados, acciones, roles, `docstatus`, `allow_edit` y `allow_self_approval` exactamente del
código. Cruzar validaciones de cada etapa con el controlador del DocType.

- [ ] **Step 2: Documentar flujos programáticos**

Cubrir como páginas separadas los entries finales de `coverage.json`: scoring/confirmación,
evidencia/trazabilidad, CAPA, informes PDF/Excel, navegación genérica, indicadores, gobierno,
procesos, obligaciones, notificaciones y scheduler. Marcar `send_email_alert=0` donde corresponda
y distinguir notificaciones implementadas por lógica propia.

- [ ] **Step 3: Aplicar plantilla obligatoria**

Cada página incluye actor, precondiciones, datos, pasos numerados, resultado tras cada paso,
estados, permisos, restricciones, negativos, evidencia, procesos relacionados y fuentes.
Representar esas 13 secciones en frontmatter `flow` tipado; `verify-coverage` rechaza campos
vacíos, estados fuera de catálogo y páginas workflow sin transiciones.

- [ ] **Step 4: Verificar contra tests/controladores**

Releer únicamente los archivos fuente declarados en coverage. Corregir cualquier discrepancia y
marcar funciones parciales/operativas.

- [ ] **Step 5: Ejecutar verificadores**

Run: `cd docs-site && npm run verify:coverage && npm run verify:links && npm run verify:privacy`  
Expected: PASS; todas las páginas y las 13 secciones estructuradas por flujo están presentes.

- [ ] **Step 6: Commit**

```bash
git add docs-site/src/content/docs/flujos docs-site/src/components docs-site/src/data/coverage.json
git commit -m "docs: documenta flujos y transiciones reales del SGC"
```

## Task 6: Construir preparación, E2E, regresión y reporte de hallazgos

**Files:**
- Create: `docs-site/src/content/docs/pruebas/preparacion.md`
- Create: `docs-site/src/content/docs/pruebas/recorrido-e2e.md`
- Create: `docs-site/src/content/docs/pruebas/regresion.md`
- Create: `docs-site/src/content/docs/pruebas/reportar-hallazgo.md`
- Create: `docs-site/src/content/docs/mapa-sistema.md`
- Create: `docs-site/src/content/docs/reglas/conceptos.md`
- Create: `docs-site/src/content/docs/reglas/permisos-estados.md`
- Create: `docs-site/src/content/docs/administracion/configuracion.md`
- Create: `docs-site/src/content/docs/administracion/procesos-periodicos.md`
- Create: `docs-site/src/content/docs/reportes-auditoria.md`
- Modify/Move/Delete: las 21 páginas existentes bajo `docs-site/src/content/docs/`

- [ ] **Step 1: Definir datos de prueba ficticios**

Usar nombres, códigos y correos reservados (`example.invalid`). Listar cuentas por rol faltantes
sin publicar identidad real.

- [ ] **Step 2: Auditar las 21 páginas existentes**

Crear una tabla temporal de decisión `conservar | reescribir | mover | eliminar` para cada página
actual (`arquitectura`, `instalacion`, `roadmap`, `manual-uso/*`, `modulos/*`, `desarrollo/*`).
Ejecutar la decisión en el mismo commit; no dejar duplicados ni links `/sgc`.

- [ ] **Step 3: Crear mapa del sistema y referencia técnica**

`mapa-sistema.md` relaciona módulos y conceptos sin inventar automatizaciones. Reescribir la
referencia técnica conservada para separar operación funcional de desarrollo y actualizar rutas,
endpoints, workflows y estado real.

- [ ] **Step 4: Escribir el E2E principal**

Recorrido: preparación → autoevaluación → evidencia/trazabilidad → valoración/scoring → revisión
DPGC → hallazgo/NC → plan/acción → cierre → informe. Cada cambio de actor queda explícito.

- [ ] **Step 5: Escribir checklist de regresión**

Cubrir login/logout, navegación, 14 roles, flujos, negativos, permisos por programa, estados,
reportes, auditoría, tareas diarias, responsive, accesibilidad y seguridad.

- [ ] **Step 6: Escribir plantilla de hallazgo**

Incluir versión/commit, URL, fecha/hora, rol, precondiciones, pasos, esperado, observado,
capturas, consola/red sin secretos y severidad reproducible.

- [ ] **Step 7: Administrar limitaciones reales**

Marcar acciones que requieren configuración, scheduler habilitado, servidor de correo, cuentas
separadas por segregación o catálogos precargados.

- [ ] **Step 8: Verificar sidebar y páginas huérfanas**

Run: `cd docs-site && npm run verify:coverage && npm run verify:links && npm run verify:orphans`  
Expected: PASS; ninguna de las páginas finales queda fuera del sidebar/manifiesto.

- [ ] **Step 9: Commit**

```bash
git add docs-site/src/content/docs
git commit -m "docs: añade recorrido E2E y regresión funcional"
```

## Task 7: Añadir verificadores automáticos y canarios

**Files:**
- Modify: `docs-site/scripts/verify-links.mjs`
- Modify: `docs-site/scripts/verify-privacy.mjs`
- Create: `docs-site/scripts/verify-dist.mjs`
- Create: `docs-site/scripts/verify-cache-config.mjs`
- Create: `docs-site/scripts/run-canary.mjs`
- Create: `docs-site/tests/visual.spec.mjs`
- Create: `docs-site/tests/contrast.spec.mjs`
- Create: `docs-site/tests/fixtures/link-broken.html`
- Modify: `docs-site/tests/fixtures/coverage-invalid.json`
- Create: `docs-site/tests/fixtures/privacy-invalid.md`
- Create: `docs-site/tests/fixtures/contrast-invalid.html`
- Create: `docs-site/tests/fixtures/nginx-cache-invalid.conf`
- Modify: `docs-site/package.json`
- Modify: `docs-site/package-lock.json`

- [ ] **Step 1: Escribir fixtures inválidas**

Crear exactamente cinco fixtures independientes: link/anchor roto, coverage inválido, DNI/correo
ficticios con patrón prohibido, contraste insuficiente y Nginx con `public` cache para contenido
protegido/base incorrecta.

- [ ] **Step 2: Implementar verificadores mínimos**

Completar `verify-links` y `verify-privacy`; `verify-dist` exige sitemap/404/Pagefind/base y rechaza
host antiguo; `verify-cache-config` parsea Nginx y rechaza caché pública/no-store ausente.

- [ ] **Step 3: Añadir Playwright + axe-core**

`contrast.spec.mjs` ejecuta axe en ambos temas. `visual.spec.mjs` prueba 1440×1000 y 390×844,
claro/oscuro, foco, búsqueda y `scrollWidth <= clientWidth`.

- [ ] **Step 4: Demostrar los canarios**

Run, uno por uno:

```bash
cd docs-site
npm run canary:links
npm run canary:coverage
npm run canary:privacy
npm run canary:contrast
npm run canary:cache-base
```

Expected: cada comando registra el exit code 1 del verificador y termina 0; el workflow muestra
cinco pasos separados. `canary:cache-base` ejecuta internamente dos mutaciones independientes
(caché pública con base correcta y base `/sgc` con caché correcta) y exige rechazo individual de
ambas para evitar enmascaramiento.

- [ ] **Step 5: Verificar sitio real**

Run: `cd docs-site && npm run verify`  
Expected: check, build, coverage, links, privacy, dist, contraste y visual PASS.

- [ ] **Step 6: Commit**

```bash
git add docs-site
git commit -m "test(docs): automatiza cobertura enlaces contraste y privacidad"
```

## Task 8: Construir la imagen estática y probar 404/caché

**Files:**
- Create: `docs-site/Dockerfile`
- Create: `docs-site/nginx.conf`
- Create: `docs-site/tests/docker-smoke.mjs`
- Modify: `.dockerignore`
- Modify: `.gitignore`
- Modify: `docs-site/package.json`

- [ ] **Step 1: Escribir smoke Docker que falle**

Exigir página, directorio, asset, extensión inexistente, 404 con cuerpo propio, `HEAD`, headers de
seguridad y políticas de caché privadas.

- [ ] **Step 2: Construir imagen multi-stage fijada**

Usar exactamente:

```dockerfile
FROM node:24-alpine@sha256:a0b9bf06e4e6193cf7a0f58816cc935ff8c2a908f81e6f1a95432d679c54fbfd AS build
FROM nginxinc/nginx-unprivileged:1.28-alpine@sha256:7377697a821c131a924a7105fafbe7414db4e9fcc77a6f08f776f33f141ec3f8
```

Ambos índices incluyen ARM64 verificado. Ejecutar `npm ci`, copiar solo `dist/` y config; añadir
healthcheck interno.

- [ ] **Step 3: Configurar Nginx sin fallback SPA**

Resolver `$uri`, `$uri/index.html`, `=404`; `error_page 404 /404.html`; `_astro` private immutable;
HTML/Pagefind/sitemap/404 private no-store; CSP, nosniff, referrer y framing.

- [ ] **Step 4: Construir y ejecutar smoke**

Run: `cd docs-site && npm run verify:docker`  
Expected: PASS; la ruta inexistente devuelve 404, nunca 200.

- [ ] **Step 5: Commit**

```bash
git add docs-site/Dockerfile docs-site/nginx.conf docs-site/tests/docker-smoke.mjs docs-site/package.json .dockerignore .gitignore
git commit -m "feat(docs): empaqueta el manual como servicio estático"
```

## Task 9: Sustituir GitHub Pages por CI de validación

**Files:**
- Modify: `.github/workflows/docs.yml`

- [ ] **Step 1: Quitar permisos y deploy de Pages**

Eliminar `pages: write`, `id-token: write`, `withastro/action` orientado a Pages y
`actions/deploy-pages`.

- [ ] **Step 2: Ejecutar matriz de validación**

Node 24, `npm ci`, `npm run verify`, Docker build/smoke y upload temporal de reportes/capturas.
Mantener los globs funcionales definidos en la especificación. Exponer cinco pasos CI separados
para los cinco canarios.

- [ ] **Step 3: Añadir job Frappe obligatorio**

Reutilizar la instalación PostgreSQL/Frappe de `.github/workflows/tests.yml` y ejecutar:

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.tests.test_manual_auth
bench --site test_site.localhost run-tests --app sgc --module sgc.tests.test_permissions
```

Expected: ambos PASS; el job es requerido cuando cambia auth o documentación protegida.

- [ ] **Step 4: Validar workflow**

Run: `actionlint .github/workflows/docs.yml`  
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/docs.yml
git commit -m "ci(docs): valida el manual sin publicarlo en Pages"
```

## Task 10: Crear el overlay productivo UPeU

**Files (repo `/Users/alberto/proyectos/upeu/upeu-ops`):**
- Create: `services/sgc/manual/institution.css`
- Create: `services/sgc/manual/canonical.env`
- Create: `services/sgc/manual/Dockerfile`
- Create: `services/sgc/manual/compose.yml`
- Create: `services/sgc/manual/scripts/release.sh`
- Create: `services/sgc/manual/scripts/smoke.mjs`
- Create: `services/sgc/manual/tests/compose.test.yml`
- Create: `services/sgc/manual/tests/run.sh`
- Create: `services/sgc/manual/tests/release-rollback.test.sh`
- Create: `services/sgc/caddy/docker-compose.yml`
- Create: `services/sgc/caddy/Caddyfile`
- Create: `services/sgc/frappe/backend-image.override.yml`
- Create: `services/sgc/frappe/backend-release.sh`
- Create: `services/sgc/frappe/backend-release.test.sh`
- Create: `.github/workflows/sgc-manual.yml`

- [ ] **Step 1: Leer `AGENTS.md` del repo cliente y comprobar estado limpio**

El repo tiene archivos ajenos sin seguimiento; no añadirlos ni modificarlos. Crear rama
`feature/sgc-manual` en un worktree global temporal fuera del repo y commitear exclusivamente
`services/sgc/**` y el workflow; no tocar `.gitignore`, `AGENTS.md` ni los untracked existentes.

Run:

```bash
git -C /Users/alberto/proyectos/upeu/upeu-ops worktree add /private/tmp/upeu-ops-sgc-manual -b feature/sgc-manual main
git -C /private/tmp/upeu-ops-sgc-manual branch --show-current
git -C /private/tmp/upeu-ops-sgc-manual status --short
```

Expected: rama `feature/sgc-manual`; estado limpio en el worktree temporal.

- [ ] **Step 2: Escribir integración fallida con upstream simulado**

Simular auth GET `204`, Guest `302` y error `503`. Exigir limpieza de `Cookie`, `Authorization`,
`X-Frappe-*`, `X-User`, `Remote-User` y headers de identidad hacia Nginx; cubrir GET/HEAD,
`/manualfoo` hacia Frappe, redirect exacta y `/manual/no-existe` 404.

- [ ] **Step 3: Crear CSS UPeU mínimo**

Derivar solo marca desde `sciback-design-system/instituciones/upeu/tokens.css`. Ejecutar
verificador de frontera y contraste claro/oscuro.

- [ ] **Step 4: Crear build multi-contexto**

`canonical` aporta `docs-site/`; `overlay` aporta `institution.css`. Hornea ambos dentro del
digest final y etiqueta con `CANONICAL_SHA-OVERLAY_SHA`. Usar los digests Node/Nginx de Task 8.

- [ ] **Step 5: Crear Caddy y Compose**

Importar exactamente la configuración productiva leída de `/opt/sgc/caddy/` a
`services/sgc/caddy/`. El Compose versionado administra `sgc-caddy`, usa
`caddy:2.11.2@sha256:25cdc846626b62d05f6b633b9b40c2c9f6ef89b515dc76133cefd920f7dbe562`
y declara `sgc-prod-net` + `sgc-proxy` como redes externas. El manual permanece solo en
`sgc-proxy`. Forward auth GET al alias `frontend`, fail-closed, redirect fija y limpieza de
credenciales. `release.sh validate-caddy` genera en temporal y valida sin mutar producción;
`activate-candidate` respalda y hace instalación atómica desde el checkout a
`/opt/sgc/caddy/{docker-compose.yml,Caddyfile}` antes del reload. Nunca depende de una conexión
manual. Ejecutar `docker compose -f services/sgc/caddy/docker-compose.yml config`.

- [ ] **Step 6: Crear promoción reproducible**

Release inmutable con `release.env`, candidato saludable, validación Caddy, smoke, puntero
`current` por rename atómico y `PREVIOUS_RELEASE_ID` encadenado.

`release.sh` debe implementar exactamente: `build`, `deploy-candidate`, `status`,
`validate-caddy` (solo lectura/no mutante), `activate-candidate`, `smoke`, `promote`, `rollback` y
`rollback --dry-run`, y `retire-previous`. `retire-previous` detiene únicamente el contenedor
anterior después del dry-run, conservando su imagen y metadatos de release; `rollback` puede
volver a arrancarlo por nombre y digest exactos. Documentar entradas y pre/postcondiciones en
`--help`. Usar `trap` para
restaurar Caddy si falla entre reload y promote. `tests/run.sh` ejercita esos mismos subcomandos;
`release-rollback.test.sh` inyecta el fallo y demuestra que upstream/current regresan al previo.

`backend-release.sh` implementa exactamente `build-and-prepare --canonical-dir DIR`, `config`,
`deploy`, `promote`, `rollback` y `status`. `build-and-prepare` obtiene el SHA con
`git -C DIR rev-parse HEAD`, inspecciona y valida la imagen actual no vacía, construye la nueva imagen y
escribe por archivo temporal + rename, modo
0600, tanto `backend-release.env.candidate` como `backend-release.env.previous`, cada uno con
`SGC_BACKEND_IMAGE=`. Su test empieza sin archivos previos y demuestra deploy/promote/rollback.

- [ ] **Step 7: Ejecutar integración**

Run: `cd services/sgc/manual && ./tests/run.sh`  
Run: `cd ../frappe && ./backend-release.test.sh`  
Expected: PASS para sesión válida/expirada/revocada/Guest/5xx, headers, caché, 404, rutas no
manuales y rollback inyectado.

- [ ] **Step 8: Configurar CI multi-repo coordinado**

El workflow lee `CANONICAL_SHA` desde el archivo versionado `services/sgc/manual/canonical.env` y
usa el secret exacto
`SCIBACK_SGC_CONTENTS_READ_TOKEN`, token fine-grained con permiso exclusivo
`SciBack/sgc:contents:read`. Ejecuta `actions/checkout@v4` con `repository: SciBack/sgc`,
`ref` igual al SHA leído, `token: ${{ secrets.SCIBACK_SGC_CONTENTS_READ_TOKEN }}` y
`persist-credentials: false`; un paso previo falla con mensaje claro si el secret está vacío.
Después ejecuta `git cat-file -e "${CANONICAL_SHA}^{commit}"`, valida que sea un commit exacto,
checkout detached y build de ambos contextos. También ejecuta `services/sgc/frappe/backend-release.test.sh`.
Documentar rotación semestral y revocación en README del servicio. No usar `main` implícito.
Inicialmente `canonical.env` apunta al commit base validado de la rama; Task 12 lo actualiza al
commit final integrado del manual antes de fusionar el overlay.

- [ ] **Step 9: Commit y push de la rama overlay**

```bash
git add services/sgc/manual services/sgc/caddy services/sgc/frappe .github/workflows/sgc-manual.yml
git commit -m "feat(sgc): integra el manual protegido en UPeU"
git push -u origin feature/sgc-manual
```

## Task 11: Verificación local completa y revisión visual

**Files:**
- Modify only files needed to correct demonstrated failures.

- [ ] **Step 1: Frontend principal**

Run: `cd frontend && npm ci && npm run build && npm run test:login-dom && npm run verify:login-design`  
Expected: PASS; warnings Rollup preexistentes documentadas, sin errores.

- [ ] **Step 2: Manual**

Run: `cd docs-site && npm ci && DOCS_SITE=https://calidad.upeu.edu.pe DOCS_BASE=/manual npm run verify`  
Expected: PASS.

- [ ] **Step 3: Imagen e integración**

Run: `cd docs-site && npm run verify:docker`  
Run overlay: `cd /private/tmp/upeu-ops-sgc-manual/services/sgc/manual && ./tests/run.sh`  
Run backend helper: `cd /private/tmp/upeu-ops-sgc-manual/services/sgc/frappe && ./backend-release.test.sh`  
Expected: PASS.

- [ ] **Step 4: Canarios**

Run: `cd docs-site && npm run verify:canaries`  
Expected: cada verificador rechaza su fixture inválida.

- [ ] **Step 5: Revisión visual real**

Abrir escritorio/móvil, claro/oscuro; capturar portada, guía de rol, flujo largo y matriz. Medir
overflow desde DOM y ejecutar axe. Aplicar revisión `emil-design-eng` en tabla Before/After.

- [ ] **Step 6: Revisión de cambios**

Run: `git diff --check && git status --short && git log --oneline main..HEAD`  
Expected: solo archivos del plan; commits pequeños y ordenados.

- [ ] **Step 7: Corregir únicamente fallos demostrados y versionarlos**

Si cualquier verificación anterior falla, conservar el canario que demuestra el fallo, aplicar la
corrección mínima, repetir la verificación afectada y las suites completas, y crear commits
selectivos en el repositorio correspondiente:

```bash
git add <archivos-canónicos-corregidos>
git commit -m "fix(docs): corrige fallos demostrados en verificación"
git -C /private/tmp/upeu-ops-sgc-manual add <archivos-overlay-corregidos>
git -C /private/tmp/upeu-ops-sgc-manual commit -m "fix(sgc): corrige integración demostrada del manual"
```

No usar `git add -A`. Ejecutar otra vez Steps 1–6 y después hacer push de ambas ramas.

## Task 12: Publicar e integrar ambas ramas coordinadamente

**Files:**
- Modify (overlay branch): `.github/workflows/sgc-manual.yml`
- Modify (overlay branch): `services/sgc/manual/canonical.env`

- [ ] **Step 1: Push de la rama canónica**

Run: `git push -u origin feature/manual-sgc-starlight`  
Expected: rama publicada.

- [ ] **Step 2: Integrar a main siguiendo el flujo del repo**

Revisar CI, fusionar la rama canónica sin reescribir historial y obtener el commit exacto con
`git rev-parse main`; ese valor es `CANONICAL_SHA`.

- [ ] **Step 3: Fijar el SHA canónico en overlay CI**

Actualizar `services/sgc/manual/canonical.env` a `CANONICAL_SHA=<sha exacto>`, ejecutar CI y fusionar
mediante:

```bash
git add services/sgc/manual/canonical.env .github/workflows/sgc-manual.yml
git commit -m "ci(sgc): fija el commit canónico del manual"
git push origin feature/sgc-manual
```

Esperar CI, fusionar `feature/sgc-manual` y registrar como `OVERLAY_SHA` el commit final que ya
contiene `CANONICAL_SHA`. No publicar aún ninguna ruta.

- [ ] **Step 4: Registrar commits exactos**

Verificar `CANONICAL_SHA` leyendo `/opt/sgc/upeu-ops/services/sgc/manual/canonical.env` después del
pull; obtener `OVERLAY_SHA` con `git rev-parse HEAD`. Los scripts de release derivan estos valores
de los checkouts y del archivo versionado: ningún paso depende de variables shell persistidas.

## Task 13: Habilitación inicial del endpoint en producción

**Files:** production checkout only; no uncommitted edits.

- [ ] **Step 1: Solicitar aprobación explícita**

Antes de reemplazar `frappe-prod-backend-1`, mostrar estado, uptime, imagen actual y rollback.

- [ ] **Step 2: Actualizar checkout por Git**

El EC2 no tiene acceso GitHub actualmente. Provisionar una vez dos deploy keys **read-only**
separadas (`~/.ssh/sgc-deploy` y `~/.ssh/upeu-ops-deploy`), registrar solo sus claves públicas
mediante `gh api repos/{owner}/{repo}/keys`, y crear aliases SSH `github-sgc` y
`github-upeu-ops`. No usar agent forwarding ni copiar una clave privada desde la Mac.

Run remoto, uno a la vez:

```bash
sudo -u ubuntu ssh-keygen -t ed25519 -N '' -f /home/ubuntu/.ssh/sgc-deploy -C sgc-app-readonly
sudo -u ubuntu ssh-keygen -t ed25519 -N '' -f /home/ubuntu/.ssh/upeu-ops-deploy -C sgc-app-ops-readonly
sudo -u ubuntu ssh-keygen -lf /home/ubuntu/.ssh/sgc-deploy.pub
sudo -u ubuntu ssh-keygen -lf /home/ubuntu/.ssh/upeu-ops-deploy.pub
```

Registrar cada `.pub` desde la Mac con `gh api -X POST repos/SciBack/sgc/keys` y
`gh api -X POST repos/UPeU-Infra/upeu-ops/keys`, `read_only=true`. Escribir en
`/home/ubuntu/.ssh/config` dos bloques con `HostName github.com`, `User git`, su `IdentityFile` y
`IdentitiesOnly yes`; verificar `git ls-remote` para ambos aliases antes de clonar.

Para cada repositorio, resolver primero si el checkout existe. Si existe, cambiar la URL antes de
cualquier acceso remoto, verificarla, probar `ls-remote` y recién entonces hacer pull:

```bash
sudo -u ubuntu git -C /opt/sgc/src/sgc remote set-url origin git@github-sgc:SciBack/sgc.git
sudo -u ubuntu git -C /opt/sgc/src/sgc remote get-url origin
sudo -u ubuntu git ls-remote git@github-sgc:SciBack/sgc.git refs/heads/main
sudo -u ubuntu git -C /opt/sgc/src/sgc pull --ff-only origin main
sudo -u ubuntu git -C /opt/sgc/src/sgc rev-parse HEAD
```

Si `/opt/sgc/src/sgc/.git` no existe, omitir esos comandos y ejecutar primero
`sudo -u ubuntu git clone git@github-sgc:SciBack/sgc.git /opt/sgc/src/sgc`; después verificar URL,
`ls-remote` y HEAD.

Aplicar la misma bifurcación al overlay:

```bash
sudo -u ubuntu git -C /opt/sgc/upeu-ops remote set-url origin git@github-upeu-ops:UPeU-Infra/upeu-ops.git
sudo -u ubuntu git -C /opt/sgc/upeu-ops remote get-url origin
sudo -u ubuntu git ls-remote git@github-upeu-ops:UPeU-Infra/upeu-ops.git refs/heads/main
sudo -u ubuntu git -C /opt/sgc/upeu-ops pull --ff-only origin main
sudo -u ubuntu git -C /opt/sgc/upeu-ops rev-parse HEAD
```

Si `/opt/sgc/upeu-ops/.git` no existe, clonar primero con
`sudo -u ubuntu git clone git@github-upeu-ops:UPeU-Infra/upeu-ops.git /opt/sgc/upeu-ops` y luego
verificar. Expected: ambos HEAD coinciden con el SHA integrado esperado y ambos `ls-remote`
funcionan sin agente reenviado. Nunca `scp`.

- [ ] **Step 3: Construir imagen Frappe overlay**

Run remoto; el helper deriva el SHA del checkout y las dos imágenes dentro de una sola invocación,
por lo que no depende de variables shell entre comandos:

```bash
cd /opt/sgc/upeu-ops/services/sgc/frappe
sudo ./backend-release.sh build-and-prepare --canonical-dir /opt/sgc/src/sgc
sudo ./backend-release.sh status
```

Expected: imagen ARM64 creada; imagen previa, nueva imagen y SHA no vacíos quedan en los archivos
0600 de candidato/previous y en el registro de despliegue.

- [ ] **Step 4: Reemplazar exclusivamente backend**

El override versionado contiene `image: ${SGC_BACKEND_IMAGE:?}`. Ejecutar:

```bash
cd /opt/sgc/upeu-ops/services/sgc/frappe
sudo ./backend-release.sh config
sudo ./backend-release.sh deploy
sudo ./backend-release.sh status
```

Expected: backend healthy/up; frontend, websocket, workers, scheduler, Redis y DB mantienen uptime.

- [ ] **Step 5: Verificar contrato auth**

Guest 302 fija; sesión válida 204; cookie auxiliar falsificada no autoriza; errores fallan cerrados.

- [ ] **Step 6: Verificar aplicación**

`/`, `/sgc/`, login local y SSO conservan su comportamiento.

- [ ] **Step 7: Promover o hacer rollback exacto**

Si verifica: `sudo ./backend-release.sh promote`. Si falla:

```bash
sudo ./backend-release.sh rollback
sudo ./backend-release.sh status
```

Expected: exclusivamente backend vuelve a la imagen previa y queda `running`.

## Task 14: Desplegar manual y Caddy sin reiniciar la aplicación

**Files:** production checkout only; no uncommitted edits.

- [ ] **Step 1: Actualizar overlay por Git**

Run remoto:

```bash
sudo -u ubuntu git -C /opt/sgc/upeu-ops remote set-url origin git@github-upeu-ops:UPeU-Infra/upeu-ops.git
sudo -u ubuntu git -C /opt/sgc/upeu-ops remote get-url origin
sudo -u ubuntu git ls-remote git@github-upeu-ops:UPeU-Infra/upeu-ops.git refs/heads/main
sudo -u ubuntu git -C /opt/sgc/upeu-ops pull --ff-only origin main
sudo -u ubuntu git -C /opt/sgc/upeu-ops rev-parse HEAD
```

Expected: HEAD sigue siendo `OVERLAY_SHA`; este paso solo revalida el checkout creado en Task 13.

- [ ] **Step 2: Construir candidato**

Run remoto:

```bash
cd /opt/sgc/upeu-ops/services/sgc/manual
sudo ./scripts/release.sh build --canonical-dir /opt/sgc/src/sgc --overlay-dir /opt/sgc/upeu-ops
sudo ./scripts/release.sh deploy-candidate
sudo ./scripts/release.sh status
```

`build` deriva `CANONICAL_SHA` del checkout canónico, lo compara con
`services/sgc/manual/canonical.env`, deriva `OVERLAY_SHA` del checkout overlay y aborta ante vacío o
discordancia. Expected: candidato `healthy`; `release.env` contiene ambos SHA, digest y container
name; Caddy aún apunta al release anterior.

- [ ] **Step 3: Validar y recargar Caddy**

Primero validar Caddy en modo estrictamente no mutante:

```bash
cd /opt/sgc/upeu-ops/services/sgc/manual
sudo ./scripts/release.sh validate-caddy
```

Expected: PASS; checksums/config validados sin instalar, recargar ni modificar
`/opt/sgc/caddy`.

Después registrar y retirar Pages, inmediatamente antes de la activación ya validada:

```bash
gh api repos/SciBack/sgc/pages > /private/tmp/sgc-pages-before.json
gh api -X DELETE repos/SciBack/sgc/pages
```

Expected: DELETE 204 y la URL GitHub Pages deja de exponer contenido. Si producción falla después,
no se reactiva Pages públicamente: se restaura Caddy a la aplicación y se reporta indisponibilidad
del manual hasta corregirla.

Luego, en EC2:

```bash
cd /opt/sgc/upeu-ops/services/sgc/manual
sudo ./scripts/release.sh activate-candidate
```

Expected: respaldo con timestamp, `caddy validate` PASS y reload en caliente; el PID/uptime de
`sgc-caddy` no cambia.

- [ ] **Step 4: Smoke anónimo y autenticado**

Run remoto: `sudo ./scripts/release.sh smoke`  
Expected: `/`, ruta interna SPA, `/manual` 308 HTTPS, `/manual/` 302 sin sesión/200 con sesión,
página interna 200, inexistente 404, GET/HEAD, cache y headers; el script no registra `sid`.

- [ ] **Step 5: Promover release**

Run remoto: `sudo ./scripts/release.sh promote`  
Expected: `current` cambia por rename atómico y el release anterior queda en
`PREVIOUS_RELEASE_ID`.

Ejecutar además `sudo ./scripts/release.sh rollback --dry-run` (solo lectura). El test de fallo
inyectado se ejecuta exclusivamente en Task 10/CI, nunca contra producción. El release anterior
no se detiene hasta terminar smoke, promote y dry-run. Después ejecutar
`sudo ./scripts/release.sh retire-previous`; conserva imagen y metadatos. Verificar que
`sudo ./scripts/release.sh rollback --dry-run` sigue resolviendo el nombre y digest exactos y que
el test automatizado ya demostró que un rollback real vuelve a arrancar ese release.

- [ ] **Step 6: Confirmar servicios**

Comparar estado y uptime de backend, frontend, websocket, workers, scheduler, Redis, Mayan y Caddy.

- [ ] **Step 7: Entrega final**

Informar URL, ruta local, páginas, roles, flujos, verificaciones, commits/digest, estado de
servicios, limitaciones y cuentas/datos E2E faltantes.
