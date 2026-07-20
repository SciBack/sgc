# Login SGC UPeU con SciBack Design System 2.0.0 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reemplazar la portada de acceso actual de Calidad UPeU por el patrón visual productivo de Pulso DTI, conservando el login Keycloak de Frappe y añadiendo tres métricas públicas agregadas.

**Architecture:** Frappe sigue generando el login y la URL OAuth. Un adaptador JavaScript mejora progresivamente el DOM existente, consume un endpoint público cacheado y monta media/hero/tarjeta sin reconstruir el flujo de autenticación. CSS Core y tema UPeU permanecen separados; si JS, API o video fallan, el acceso nativo sigue utilizable.

**Tech Stack:** Frappe 16.25/Python 3.14, JavaScript ES2020 sin framework para la web pública, CSS custom properties, Docker Compose ARM64, Keycloak OIDC, pruebas Frappe `IntegrationTestCase`, Node.js para verificadores, Playwright/Chrome para validación visual.

**Spec:** `docs/superpowers/specs/2026-07-20-login-sgc-sciback-ds-2-design.md`

---

## Mapa de archivos

| Archivo | Responsabilidad |
| --- | --- |
| `sgc/login_portada.py` | Contrato público y cacheado de métricas agregadas |
| `sgc/tests/test_login_portada.py` | Filtros, contrato, cero denominador, whitelist guest y caché |
| `sgc/public/css/sciback_core.css` | Tokens semánticos SciBack 2.0 adaptados a CSS nativo |
| `sgc/public/css/themes/upeu.css` | Únicamente tokens de marca UPeU |
| `sgc/public/css/sgc_web.css` | Composición de portada, responsive, estados y movimiento |
| `sgc/public/js/sgc_web.js` | Mejora progresiva del login, métricas, fallbacks y break-glass |
| `sgc/public/media/login/*` | Video, póster y logo blanco autoalojados |
| `sgc/public/fonts/*` | Archivo y Public Sans autoalojadas desde paquetes Fontsource fijados por lockfile |
| `sgc/hooks.py` | Orden de carga Core → tema → portada |
| `sgc/tests/test_login_assets.py` | Contrato estático de hooks, rutas, textos y reglas críticas |
| `frontend/scripts/verificar-*.mjs` | Frontera institucional, tokens usados y contraste |
| `frontend/scripts/fixtures/institucion-invalida.css` | Canary negativo del límite Core/tema institucional |
| `frontend/tests/sgc_web.test.mjs` | Pruebas DOM del adaptador con Node Test + JSDOM |
| `frontend/package.json` / `package-lock.json` | Comandos de pruebas/verificación y dependencia JSDOM |
| `.dockerignore` | Contexto mínimo y reproducible para la imagen overlay |
| `deploy/Dockerfile.overlay` | Imagen de la app completa sobre la imagen productiva vigente |
| `docs-site/src/content/docs/instalacion.md` | Runbook de break-glass y verificación posterior al despliegue |

No se modifica `frontend/src/**`, la SPA `/sgc`, Desk ni los DocTypes.

### Task 1: Endpoint público de métricas

**Files:**
- Create: `sgc/login_portada.py`
- Create: `sgc/tests/test_login_portada.py`

- [ ] **Step 1: Escribir la prueba fallida del contrato**

Crear un `IntegrationTestCase` que limpie `sgc:login-portada:v1`, invoque
`metricas_portada()` y exija exactamente:

```python
self.assertEqual(
    set(payload),
    {"programas", "autoevaluaciones", "evidencias", "calculado_en"},
)
self.assertEqual(set(payload["programas"]), {"activos", "sedes"})
self.assertEqual(set(payload["autoevaluaciones"]), {"activas", "total", "pct"})
self.assertEqual(set(payload["evidencias"]), {"vigentes", "con_vigencia", "pct"})
self.assertIn(metricas_portada, frappe.whitelisted)
self.assertIn(metricas_portada, frappe.allowed_guest_methods)
```

Añadir casos independientes para:

- `Programa Sede.estado == "activo"` y sedes distintas;
- Autoevaluación activa solo con `docstatus=0` y estado `Planificada|En curso|En revision`;
- total de autoevaluaciones con `docstatus < 2`;
- evidencia vigente por `vigencia_hasta >= today`;
- `evidencias.pct is None` cuando el denominador es cero;
- segunda llamada servida desde caché aunque cambie una fila en DB.

- [ ] **Step 2: Ejecutar y confirmar el fallo**

Run:

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_portada
```

Expected: FAIL con `ModuleNotFoundError: No module named 'sgc.login_portada'`.

- [ ] **Step 3: Implementar el endpoint mínimo**

Usar este contrato:

```python
from datetime import datetime
from zoneinfo import ZoneInfo

import frappe
from frappe.utils import get_system_timezone, nowdate

_CACHE_KEY = "sgc:login-portada:v1"
_CACHE_TTL = 300
_AE_ACTIVAS = ("Planificada", "En curso", "En revision")

def _pct(numerador: int, denominador: int) -> int | None:
    return round(numerador * 100 / denominador) if denominador else None

def _calcular() -> dict:
    hoy = nowdate()
    programas = frappe.get_all(
        "Programa Sede",
        filters={"estado": "activo"},
        fields=["sede"],
        ignore_permissions=True,
    )
    ae_total = frappe.db.count("Autoevaluacion", {"docstatus": ["<", 2]})
    ae_activas = frappe.db.count(
        "Autoevaluacion",
        {"docstatus": 0, "estado": ["in", _AE_ACTIVAS]},
    )
    ev_total = frappe.db.count("Evidencia", {"vigencia_hasta": ["is", "set"]})
    ev_vigentes = frappe.db.count(
        "Evidencia",
        {"vigencia_hasta": [">=", hoy]},
    )
    return {
        "programas": {
            "activos": len(programas),
            "sedes": len({row.sede for row in programas if row.sede}),
        },
        "autoevaluaciones": {
            "activas": ae_activas,
            "total": ae_total,
            "pct": _pct(ae_activas, ae_total),
        },
        "evidencias": {
            "vigentes": ev_vigentes,
            "con_vigencia": ev_total,
            "pct": _pct(ev_vigentes, ev_total),
        },
        "calculado_en": datetime.now(
            ZoneInfo(get_system_timezone())
        ).isoformat(timespec="seconds"),
    }

@frappe.whitelist(allow_guest=True)
def metricas_portada() -> dict:
    if cached := frappe.cache.get_value(_CACHE_KEY):
        return cached
    payload = _calcular()
    frappe.cache.set_value(_CACHE_KEY, payload, expires_in_sec=_CACHE_TTL)
    return payload
```

No aceptar parámetros públicos. No devolver nombres, IDs ni filas.
La prueba del contrato debe exigir que `calculado_en` termine en un offset `±HH:MM`; no
aceptar un datetime ingenuo.

- [ ] **Step 4: Ejecutar pruebas y corregir solo lo necesario**

Run:

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_portada
```

Expected: PASS; la prueba de cache observa el mismo payload durante 300 s.

- [ ] **Step 5: Commit**

```bash
git add sgc/login_portada.py sgc/tests/test_login_portada.py
git commit -m "feat(sgc): expone métricas públicas de la portada"
```

### Task 2: Tokens SciBack Core y tema UPeU

**Files:**
- Create: `sgc/public/css/sciback_core.css`
- Create: `sgc/public/css/themes/upeu.css`
- Modify: `sgc/hooks.py:29-31`
- Create: `frontend/scripts/verificar-capa-institucional.mjs`
- Create: `frontend/scripts/verificar-capa-institucional-canary.mjs`
- Create: `frontend/scripts/verificar-tokens-login.mjs`
- Create: `frontend/scripts/verificar-contraste-login.mjs`
- Create: `frontend/scripts/fixtures/institucion-invalida.css`
- Modify: `frontend/package.json:6-10`

- [ ] **Step 1: Crear primero el verificador de frontera**

Copiar desde
`/Users/alberto/proyectos/sciback/sciback-design-system/canonico/scripts/verificar-capa-institucional.mjs`
y ejecutarlo inicialmente contra el CSS actual para confirmar que todavía no existe la capa:

```bash
cd frontend
node scripts/verificar-capa-institucional.mjs ../sgc/public/css/themes/upeu.css
```

Expected: FAIL `ENOENT`.

- [ ] **Step 2: Crear Core y tema con responsabilidades separadas**

`sciback_core.css` declara en `:root` los tokens de
`/Users/alberto/proyectos/sciback/sciback-design-system/canonico/tokens.css` como CSS custom
properties normales:
`fondo`, `superficie*`, `borde*`, `tinta*`, `accion*`, estados, series, rejilla y
niveles. Mantener el bloque `.dark` aunque el login sea superficie fija.

`themes/upeu.css` se deriva de
`/Users/alberto/proyectos/sciback/sciback-design-system/instituciones/upeu/tokens.css`
y contiene exclusivamente esta rampa completa:

```css
:root {
  --color-marca-primaria-50: #eef4fa;
  --color-marca-primaria-100: #d8e6f3;
  --color-marca-primaria-200: #b3cde6;
  --color-marca-primaria-300: #7fadd4;
  --color-marca-primaria-400: #4a90d9;
  --color-marca-primaria-500: #2166ac;
  --color-marca-primaria-600: #0f4c81;
  --color-marca-primaria-700: #003366;
  --color-marca-primaria-800: #002a54;
  --color-marca-primaria-900: #001f3f;
  --color-marca-secundaria-50: #fff8e6;
  --color-marca-secundaria-100: #ffefc2;
  --color-marca-secundaria-200: #ffe08a;
  --color-marca-secundaria-300: #fcc94d;
  --color-marca-secundaria-400: #fab724;
  --color-marca-secundaria-500: #f8a900;
  --color-marca-secundaria-600: #d98f00;
  --color-marca-secundaria-700: #b45309;
  --color-marca-secundaria-800: #92400e;
  --color-sobre-marca-primaria: #ffffff;
  --color-sobre-marca-secundaria: #17253a;
}
```

No introducir `--color-fondo`, estados, radios, sombras o espaciado en el tema UPeU.

- [ ] **Step 3: Cargar hojas en orden**

```python
web_include_css = [
    "/assets/sgc/css/sciback_core.css",
    "/assets/sgc/css/themes/upeu.css",
    "/assets/sgc/css/sgc_web.css",
]
```

Mantener `web_include_js` sin cambio.

- [ ] **Step 4: Añadir verificadores del consumidor**

`verificar-tokens-login.mjs` debe leer Core + tema + `sgc_web.css`, recopilar todas las
declaraciones `--color-*` y fallar si un `var(--color-*)` usado no está declarado.

`verificar-contraste-login.mjs` debe medir al menos:

- blanco sobre `marca-primaria-700` ≥ 4.5;
- `#17253a` sobre blanco ≥ 4.5;
- `#62748c` sobre blanco ≥ 4.5;
- cromo de borde sobre blanco ≥ 3;
- dorado solo como relleno/acento, nunca como tinta normal.

Agregar:

```json
"verify:login-design:canary": "node scripts/verificar-capa-institucional-canary.mjs",
"verify:login-design": "node scripts/verificar-capa-institucional.mjs ../sgc/public/css/themes/upeu.css && npm run verify:login-design:canary && node scripts/verificar-tokens-login.mjs && node scripts/verificar-contraste-login.mjs"
```

El canary ejecuta el verificador institucional contra
`scripts/fixtures/institucion-invalida.css`, que declara deliberadamente
`--color-fondo`, y solo pasa si el proceso hijo termina con código `1`. Así se comprueba que
el verificador no produce un falso verde.

- [ ] **Step 5: Verificar y commit**

```bash
cd frontend
npm run verify:login-design
cd ..
git add sgc/hooks.py sgc/public/css/sciback_core.css sgc/public/css/themes/upeu.css frontend/scripts frontend/package.json
git commit -m "feat(ui): adopta tokens SciBack 2.0 en la web pública"
```

Expected: verificador institucional, canary, tokens y contraste en verde.

### Task 3: Activos institucionales autoalojados

**Files:**
- Create: `sgc/public/media/login/oficinas-dti.mp4`
- Create: `sgc/public/media/login/oficinas-dti-poster.jpg`
- Create: `sgc/public/media/login/upeu-logo-2026-white.svg`
- Create: `sgc/public/fonts/archivo-latin-700-normal.woff2`
- Create: `sgc/public/fonts/public-sans-latin-400-normal.woff2`
- Create: `sgc/public/fonts/public-sans-latin-600-normal.woff2`
- Create: `sgc/public/fonts/public-sans-latin-700-normal.woff2`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Verificar las fuentes exactas**

```bash
ls -lh /Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti.mp4 /Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti-poster.jpg /Users/alberto/proyectos/upeu/branding/logos/2026-web/upeu-logo-2026-white.svg
```

Expected: MP4 ~1.5 MB, póster ~93 KB y logo SVG presente.

- [ ] **Step 2: Copiar a la ruta versionada del consumidor**

```bash
mkdir -p sgc/public/media/login
cp /Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti.mp4 sgc/public/media/login/oficinas-dti.mp4
cp /Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti-poster.jpg sgc/public/media/login/oficinas-dti-poster.jpg
cp /Users/alberto/proyectos/upeu/branding/logos/2026-web/upeu-logo-2026-white.svg sgc/public/media/login/upeu-logo-2026-white.svg
cd frontend && npm install --save-dev @fontsource/archivo @fontsource/public-sans && cd ..
mkdir -p sgc/public/fonts
cp frontend/node_modules/@fontsource/archivo/files/archivo-latin-700-normal.woff2 sgc/public/fonts/archivo-latin-700-normal.woff2
cp frontend/node_modules/@fontsource/public-sans/files/public-sans-latin-400-normal.woff2 sgc/public/fonts/public-sans-latin-400-normal.woff2
cp frontend/node_modules/@fontsource/public-sans/files/public-sans-latin-600-normal.woff2 sgc/public/fonts/public-sans-latin-600-normal.woff2
cp frontend/node_modules/@fontsource/public-sans/files/public-sans-latin-700-normal.woff2 sgc/public/fonts/public-sans-latin-700-normal.woff2
```

Esta es una operación local de construcción del repo, no un despliegue por `scp`.
`package-lock.json` fija las versiones exactas resueltas de Fontsource.

- [ ] **Step 3: Verificar codecs y faststart**

```bash
ffprobe -v error -show_entries stream=codec_name,codec_type:format=duration,size -of json sgc/public/media/login/oficinas-dti.mp4
```

Expected: video H.264, sin stream de audio, tamaño cercano a 1.5 MB. Ejecutar
`ffprobe -v trace ... | rg 'type.*moov|type.*mdat'` y comprobar `moov` antes de `mdat`.
No recomprimir si ya cumple.

- [ ] **Step 4: Verificar SVG y tamaños**

```bash
file sgc/public/media/login/*
du -h sgc/public/media/login/*
file sgc/public/fonts/*.woff2
```

Expected: tipos correctos; ningún activo externo ni symlink.

- [ ] **Step 5: Commit**

```bash
git add sgc/public/media/login sgc/public/fonts frontend/package.json frontend/package-lock.json
git commit -m "feat(ui): autoaloja media de la portada SGC"
```

### Task 4: Mejora progresiva del login

**Files:**
- Modify: `sgc/public/js/sgc_web.js:1-41`
- Create: `sgc/tests/test_login_assets.py`
- Create: `frontend/tests/sgc_web.test.mjs`
- Modify: `frontend/package.json`
- Modify: `frontend/package-lock.json`

- [ ] **Step 1: Escribir pruebas estáticas y DOM fallidas**

`test_login_assets.py` debe leer `sgc_web.js` y exigir:

```python
self.assertIn('URLSearchParams(window.location.search).get("login_local") === "1"', js)
self.assertIn("a.btn-keycloak", js)
self.assertIn("sgc.login_portada.metricas_portada", js)
self.assertIn("AbortSignal.timeout(4000)", js)
self.assertNotIn("oauth2_logins", js)
```

También debe verificar que el código contiene los textos aprobados y las tres rutas
`/assets/sgc/media/login/*`.

Instalar `jsdom@^26.1.0` como dependencia de desarrollo y crear
`frontend/tests/sgc_web.test.mjs` con `node:test`, `node:assert/strict` y JSDOM. El fixture
incluye un enlace original:

```bash
cd frontend && npm install --save-dev jsdom@^26.1.0 && cd ..
```

```html
<div class="alert alert-danger" role="alert">No se pudo completar el acceso.</div>
<a class="btn-keycloak"
   href="https://keyid.upeu.edu.pe/realms/upeu/protocol/openid-connect/auth?state=ORIGINAL">
  Ingresar con cuenta institucional
</a>
```

Cubrir estos comportamientos, no solo cadenas del fuente:

- dos ejecuciones de `start()` producen un solo `#sgc-login-cover`;
- el CTA montado es exactamente el mismo nodo del fixture y conserva sin cambios su
  `href`, incluido `state=ORIGINAL`;
- el elemento de error separado sobrevive al montaje como el mismo nodo, conserva su texto
  y `role="alert"`; el CTA no recibe rol de alerta;
- `?login_local=1` no monta portada ni clase `sgc-login`;
- un `fetch` rechazado mantiene visible el enlace SSO y deja las métricas en fallback;
- una respuesta `{message: payload}` pinta las tres métricas;
- `evidencias.pct: null` deja `—` y no produce `NaN` ni una barra inválida.

Agregar `"test:login-dom": "node --test tests/sgc_web.test.mjs"`.

- [ ] **Step 2: Ejecutar y confirmar el fallo**

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_assets
cd frontend && npm run test:login-dom
```

Expected: ambas fallan porque la portada todavía no está montada.

- [ ] **Step 3: Reescribir el adaptador de manera idempotente**

Implementar funciones pequeñas:

- `esLoginLocal()`: devuelve true con `?login_local=1`;
- `crearEstructura()`: monta una sola vez `#sgc-login-cover`;
- `adaptarTarjeta(card)`: mueve, no clona, el enlace `a.btn-keycloak`;
- `cargarMetricas()`: fetch a
  `/api/method/sgc.login_portada.metricas_portada` con timeout 4 s, exige `response.ok`,
  lee `await response.json()` y entrega `json.message` a `pintarMetricas()`;
- `pintarMetricas(payload)`: solo usa `textContent` y valores numéricos validados;
- `activarFallback()`: deja `—` y textos de fallback;
- `start()`: si es break-glass no añade `sgc-login`; si no, mejora el DOM y observa
  re-render durante cinco segundos.

Reglas:

- no construir ni editar `href` OAuth;
- no usar `innerHTML` con datos de API;
- el enlace Keycloak debe seguir siendo el nodo original;
- video con `aria-hidden=true`;
- microvisualizaciones con `aria-hidden=true`;
- enlaces de guía/ayuda solo si tienen URL real; en esta fase usar la guía existente
  `https://sciback.github.io/sgc/manual-uso/primeros-pasos/` y omitir Centro de ayuda si
  no existe destino real;
- bajo `prefers-reduced-motion: reduce`, no asignar `autoplay` al video.

- [ ] **Step 4: Ejecutar pruebas**

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_assets
cd frontend && npm run test:login-dom
```

Expected: PASS en contrato estático y comportamiento DOM; ausencia de URLs OAuth
hardcodeadas en el adaptador.

- [ ] **Step 5: Commit**

```bash
git add sgc/public/js/sgc_web.js sgc/tests/test_login_assets.py frontend/tests/sgc_web.test.mjs frontend/package.json frontend/package-lock.json
git commit -m "feat(ui): monta portada SGC sobre el login nativo"
```

### Task 5: Composición visual responsive

**Files:**
- Modify: `sgc/public/css/sgc_web.css:1-82`
- Modify: `sgc/tests/test_login_assets.py`

- [ ] **Step 1: Ampliar la prueba con reglas no negociables**

Exigir selectores para `.sgc-login-cover`, `.sgc-login-hero`,
`.sgc-login-stats`, `.sgc-login-card`, breakpoint `1024px` y
`prefers-reduced-motion`. Exigir además cuatro reglas `@font-face` cuyas URLs apunten a
`/assets/sgc/fonts/*.woff2`. Fallar si aparecen:

```python
self.assertNotIn("transition: all", css)
self.assertNotIn("ease-in", css)
self.assertNotRegex(css, r"\.sgc-login-video[^}]*filter\s*:")
self.assertNotRegex(css, r"transform\s*:\s*scale\(0\)")
```

- [ ] **Step 2: Confirmar el fallo**

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_assets
```

Expected: FAIL por selectores ausentes.

- [ ] **Step 3: Implementar el CSS aprobado**

Trasladar la anatomía del mockup aprobado y de Pulso DTI:

- video edge-to-edge + tres velos, sin blur;
- header UPeU + `SGC UPeU`;
- hero Archivo 700 y cuerpo Public Sans 400/600/700, todos autoalojados con
  `font-display: swap` y fallbacks del sistema;
- tres stat cards, único lugar con `backdrop-filter`;
- tarjeta clara fija, 28px, sombra flotante;
- CTA con `:active { transform: scale(.97) }`;
- dos columnas solo con `min-width: 1024px`;
- hero oculto en tablet/móvil;
- fallback navy cuando falla el media;
- footer aprobado.

Usar solo tokens de Core/UPeU o hexes comentados para la superficie institucional fija.
No animar `width`; las barras se pintan con `transform: scaleX()` y
`transform-origin:left`.

- [ ] **Step 4: Ejecutar pruebas y verificadores**

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_assets
cd frontend && npm run verify:login-design
```

Expected: PASS y tres verificadores en verde.

- [ ] **Step 5: Commit**

```bash
git add sgc/public/css/sgc_web.css sgc/tests/test_login_assets.py
git commit -m "feat(ui): aplica portada institucional responsive al SGC"
```

### Task 6: Verificación integrada local

**Files:**
- Modify: `docs-site/src/content/docs/instalacion.md`
- Create: `.dockerignore`
- Create: `deploy/Dockerfile.overlay`

- [ ] **Step 1: Crear el overlay reproducible de despliegue**

Crear `.dockerignore` excluyendo `.git`, `.superpowers`, `frontend/node_modules`,
`frontend/dist`, `docs-site/node_modules`, `__pycache__` y `*.pyc`. No excluir
`sgc/public/frontend` ni `sgc/public/media`, porque ambos deben llegar compilados a la imagen.

Crear `deploy/Dockerfile.overlay`:

```dockerfile
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
COPY --chown=frappe:frappe . /home/frappe/frappe-bench/apps/sgc
RUN cd /home/frappe/frappe-bench && bench build --app sgc
```

El argumento obligatorio evita asumir `v47`, `v69` u otra etiqueta desactualizada: la base
se obtiene del contenedor `backend` que realmente está corriendo.

- [ ] **Step 2: Documentar operación y break-glass**

Añadir rutas:

- login normal: `/login?redirect-to=/sgc`;
- emergencia local: `/login?login_local=1`;
- endpoint: `/api/method/sgc.login_portada.metricas_portada`;
- rollback de CSS/JS/media;
- origen provisional del video.

- [ ] **Step 3: Ejecutar la suite focal y completa**

```bash
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_portada
bench --site sgc.localhost run-tests --app sgc --module sgc.tests.test_login_assets
bench --site sgc.localhost run-tests --app sgc
cd frontend && npm run test:login-dom && cd ..
```

Expected: todas PASS.

- [ ] **Step 4: Compilar y validar diseño**

```bash
cd frontend
npm run build
npm run verify:login-design
node scripts/verificar-capa-institucional-canary.mjs
cd ..
git diff --check
```

Expected: build exitoso, verificadores verdes y diff sin whitespace errors.

- [ ] **Step 5: Validar en navegador local**

Con Chrome/Playwright, capturar:

- 1440×1000;
- 834×1112;
- 390×844;
- 1440×1000 con `reducedMotion: "reduce"`.

Comprobar: sin scroll horizontal; hero solo desktop; tarjeta visible sin animación; video
nítido; SSO conserva host `keyid.upeu.edu.pe`; break-glass muestra formulario local; API
caída y video bloqueado mantienen acceso.

- [ ] **Step 6: Commit**

```bash
git add .dockerignore deploy/Dockerfile.overlay docs-site/src/content/docs/instalacion.md
git commit -m "docs: documenta operación de la portada SGC"
```

### Task 7: Publicación y despliegue productivo

**Files:**
- No source changes expected unless validation finds a defect.

- [ ] **Step 1: Verificar estado final y publicar**

```bash
git status --short
git log -6 --oneline
git push origin main
```

Expected: worktree limpio y commits publicados.

- [ ] **Step 2: Diagnóstico de solo lectura en sgc-app**

```bash
ssh -i /Users/alberto/.ssh/kp-ohio-research.pem ubuntu@3.18.90.66 "cd /opt/sgc/build-portal/sgc-repo && git status --short --branch && git remote -v && cd /opt/sgc/frappe-prod && docker compose ps"
```

Expected: clon en rama conocida, sin cambios locales superpuestos y stack saludable. Si el
clon está sucio, detenerse; no sobrescribir.

- [ ] **Step 3: Actualizar el clon y construir una imagen inmutable**

```bash
ssh -i /Users/alberto/.ssh/kp-ohio-research.pem ubuntu@3.18.90.66 "cd /opt/sgc/build-portal/sgc-repo && git pull --ff-only origin main && git rev-parse --short HEAD"
```

Verificar que el SHA coincide con local. Derivar la imagen base desde el `backend` en ejecución,
exigir una etiqueta `v<entero>`, construir el siguiente número y guardar la transición:

```bash
ssh -i /Users/alberto/.ssh/kp-ohio-research.pem ubuntu@3.18.90.66 'set -e; cd /opt/sgc/frappe-prod; backend_id=$(docker compose ps -q backend); test -n "$backend_id"; current_image=$(docker inspect -f "{{.Config.Image}}" "$backend_id"); current_num=${current_image##*:v}; [[ "$current_num" =~ ^[0-9]+$ ]] || { echo "Etiqueta no versionada: $current_image"; exit 1; }; new_image="sgc-frappe:v$((current_num + 1))"; cd /opt/sgc/build-portal; docker build --build-arg BASE_IMAGE="$current_image" -t "$new_image" -f sgc-repo/deploy/Dockerfile.overlay sgc-repo; printf "%s\n%s\n" "$current_image" "$new_image" > /tmp/sgc-login-image-transition.txt; docker image inspect --format "actual={{index .RepoTags 0}} bytes={{.Size}}" "$current_image"; docker image inspect --format "nueva={{index .RepoTags 0}} bytes={{.Size}}" "$new_image"'
```

No editar todavía `/opt/sgc/frappe-prod/docker-compose.yml` ni recrear servicios. Si la
etiqueta vigente no termina en `:v<entero>`, detenerse y corregir el plan con el valor real.

- [ ] **Step 4: Pedir aprobación antes de recrear servicios críticos**

Presentar: tag actual, tag nuevo, SHA, resultado de tests, tamaño de imagen y este rollback
exacto:

```bash
ssh -i /Users/alberto/.ssh/kp-ohio-research.pem ubuntu@3.18.90.66 'cp /opt/sgc/frappe-prod/docker-compose.yml.rollback-login /opt/sgc/frappe-prod/docker-compose.yml && cd /opt/sgc/frappe-prod && docker compose up -d && docker compose ps'
```

Esperar aprobación explícita antes de modificar el compose o ejecutar `docker compose up -d`.

- [ ] **Step 5: Aplicar, migrar y verificar**

Tras aprobación:

```bash
ssh -i /Users/alberto/.ssh/kp-ohio-research.pem ubuntu@3.18.90.66 'set -e; current_image=$(sed -n "1p" /tmp/sgc-login-image-transition.txt); new_image=$(sed -n "2p" /tmp/sgc-login-image-transition.txt); test -n "$current_image"; test -n "$new_image"; cd /opt/sgc/frappe-prod; cp docker-compose.yml docker-compose.yml.rollback-login; test "$(grep -Fc "image: $current_image" docker-compose.yml)" -eq 1; sed -i "s|image: $current_image|image: $new_image|" docker-compose.yml; test "$(grep -Fc "image: $new_image" docker-compose.yml)" -eq 1; grep -nF "image: $new_image" docker-compose.yml; docker compose up -d; docker compose exec -T backend bench --site calidad.upeu.edu.pe migrate; docker compose exec -T backend bench --site calidad.upeu.edu.pe clear-cache; docker compose ps'
```

Verificar inmediatamente:

```bash
curl -fsS https://calidad.upeu.edu.pe/api/method/sgc.login_portada.metricas_portada
curl -fsSI "https://calidad.upeu.edu.pe/login?redirect-to=/sgc"
curl -fsSI "https://calidad.upeu.edu.pe/login?login_local=1"
```

Luego ejecutar Playwright sobre producción en los cuatro viewports y un login SSO real hasta
Keycloak. Si falla una verificación, ejecutar el rollback exacto de Step 4 y confirmar con
`docker compose ps`, los tres `curl` y el host Keycloak antes de diagnosticar.

---

## Criterio de finalización

- Endpoint público cumple contrato, cache y cero PII.
- Portada coincide con la dirección aprobada y con Pulso DTI.
- SSO original y break-glass funcionan.
- Sin blur en video, sin enlaces falsos, sin animaciones que oculten contenido.
- Pruebas Frappe, build, verificadores, accesibilidad y viewports en verde.
- Producción verificada después del despliegue y rollback documentado.
