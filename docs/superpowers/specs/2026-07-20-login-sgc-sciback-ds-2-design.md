# Diseño: portada de acceso SGC UPeU con SciBack Design System 2.0.0

**Fecha:** 2026-07-20  
**Estado:** aprobado visualmente por Alberto  
**Referencia visual:** portada productiva de Pulso DTI (`https://pulso-dti.upeu.edu.pe/`)  
**Sistema visual:** SciBack Design System `2.0.0` + tema institucional UPeU

## 1. Objetivo

Rediseñar únicamente la página de acceso de `https://calidad.upeu.edu.pe/` para que use el
mismo patrón visual de Pulso DTI: media institucional a pantalla completa, velos navy, hero
editorial con tres métricas agregadas y tarjeta SSO flotante. La autenticación existente con
Keycloak/Microsoft 365 se conserva sin cambios funcionales.

La interfaz autenticada de `/sgc`, las páginas web heredadas y Frappe Desk quedan fuera de esta
entrega. Se diseñarán en una fase posterior.

## 2. Decisiones aprobadas

- La portada seguirá la composición de Pulso DTI, no una reinterpretación aproximada.
- El video `oficinas-dti` de Pulso DTI se usará como activo provisional.
- El video se autoalojará en Calidad UPeU; no se enlazará en producción desde Pulso DTI ni desde
  un CDN externo.
- La portada es una superficie institucional fija: no cambia entre modo claro y oscuro.
- Para la futura aplicación autenticada, el modo claro será el predeterminado y el oscuro será
  seleccionable y persistente. Esa capacidad no forma parte de esta entrega.
- Copia principal aprobada:
  - eyebrow: `Dirección de Gestión de la Calidad`;
  - titular: `Calidad que se demuestra.`;
  - apoyo: `Acreditación, evidencias y mejora continua — conectadas, trazables y medibles.`
- La tarjeta de acceso usará `SGC`, `Bienvenido al SGC` y el CTA
  `Ingresar con mi cuenta UPeU`.

## 3. Arquitectura

La página continúa siendo el login nativo de Frappe. No se crea una segunda ruta ni un flujo
de autenticación paralelo.

### 3.1 Capas

1. **Frappe login:** conserva formulario, estados, errores, enlace OAuth y redirección.
2. **Adaptador de portada:** `sgc_web.js` detecta `body[data-path="login"]`, añade la estructura
   visual alrededor del contenido existente y reutiliza el enlace Keycloak ya generado por
   Frappe. Nunca reconstruye manualmente la URL OAuth ni su `state`.
3. **Estilos:** `sgc_web.css` consume variables semánticas compatibles con SciBack Design
   System 2.0.0. Los colores UPeU quedan limitados al cromo de marca.
4. **Media institucional:** video MP4 optimizado, póster JPG y logo blanco oficial, todos
   servidos desde `/assets/sgc/`.
5. **Métricas públicas:** método Frappe de solo lectura, `allow_guest`, que devuelve únicamente
   agregados no personales y cacheados durante 300 segundos.

### 3.2 Separación SciBack/UPeU

SciBack conserva neutros, geometría, movimiento, estados y reglas de contraste. La capa UPeU
aporta `#003366`, `#f8a900`, tintas sobre marca y activos oficiales. El video, logo y copia de
la Dirección de Gestión de la Calidad son overlay institucional; no se presentan como parte
del núcleo canónico del design system.

## 4. Composición y componentes

### 4.1 Fondo

- Video edge-to-edge, nítido y sin `filter: blur()`.
- Tres velos: vertical, horizontal y radial localizado para asegurar lectura del logo y hero.
- Póster visible antes de que el video esté listo.
- Video `autoplay muted loop playsinline`; si no carga, el póster mantiene la composición.

### 4.2 Header

- Logo UPeU blanco oficial, separador vertical y nombre `SGC UPeU`.
- Arriba a la izquierda en escritorio; centrado en tablet/móvil.
- El SVG proviene de `~/proyectos/upeu/branding/logos/2026-web/upeu-logo-2026-white.svg`.

### 4.3 Hero

- Visible únicamente desde `1024px`.
- Archivo para titulares; Public Sans para cuerpo e interfaz.
- Texto blanco con sombra sobre video; eyebrow en dorado como relleno/acento, nunca como texto
  corriente sobre superficie clara.
- Tres métricas con `tabular-nums`, tarjetas translúcidas y `backdrop-filter` limitado a ellas.

Métricas y consultas aprobadas:

| Métrica | Definición pública exacta |
| --- | --- |
| Programas académicos | `count(Programa Sede)` con `estado = "activo"`; `sedes` es el conteo distinto del campo `sede` sobre ese mismo conjunto |
| Autoevaluaciones activas | `count(Autoevaluacion)` con `docstatus = 0` y `estado in ("Planificada", "En curso", "En revision")`; el total comparativo incluye todo registro con `docstatus < 2` |
| Evidencias vigentes | denominador: evidencias con `vigencia_hasta` no vacío; numerador: las que cumplen `vigencia_hasta >= today`; el porcentaje se redondea al entero más cercano |

Si el denominador de evidencias es cero, `pct` es `null` y la portada muestra `—`, no `0%`.
Si cualquier métrica no puede calcularse, se muestra `—`, nunca un valor inventado.

Microvisualizaciones, siempre decorativas y con texto equivalente visible:

- **Programas:** un punto por sede activa, con máximo visual de seis; el texto muestra
  `en N sedes` y conserva el dato completo aunque haya más de seis.
- **Autoevaluaciones:** barra `activas / total`; si el total es cero, ancho cero y texto
  `sin autoevaluaciones registradas`.
- **Evidencias:** barra de ancho `pct`; si `pct` es `null`, no se pinta relleno y el texto dice
  `sin control de vigencia`.

Las barras y puntos llevan `aria-hidden="true"`; la cifra y el texto adyacentes expresan toda la
información sin depender de forma o color.

### 4.4 Tarjeta SSO

- Superficie clara fija, nítida, `rounded-2xl`/28px y sombra flotante.
- Marca `SGC`, título, texto breve, divisor dorado y CTA institucional.
- El CTA reutiliza el `<a>` Keycloak que genera Frappe.
- Enlaces `Guía de inicio` y `Centro de ayuda` solo se muestran si tienen destino real. No se
  publican enlaces `#`.
- Mensajes de error OAuth permanecen visibles, con `role="alert"`.
- El login local de emergencia permanece funcional mediante la URL directa
  `/login?login_local=1`. En esa ruta `sgc_web.js` no monta la portada SSO y deja visible el
  formulario nativo de Frappe. No habrá enlace público hacia esa ruta; se documentará en el
  runbook operativo y se probará después de cada despliegue.

### 4.5 Footer

`© 2026 SGC UPeU · Universidad Peruana Unión · Dirección de Gestión de la Calidad`.

## 5. Responsive y movimiento

- Dos columnas únicamente desde `1024px`.
- En tablet y móvil se ocultan hero y métricas; se conservan header, tarjeta SSO y fondo.
- Zonas pulsables de al menos `44×44px`.
- CTA con `scale(0.97)` en `:active`.
- Entradas `ease-out`, menores de 300ms y limitadas a `transform`/`opacity`.
- La opacidad de la tarjeta es estática; la animación nunca controla su visibilidad base.
- `prefers-reduced-motion` elimina desplazamientos y conserva cambios de color/opacidad.
- El video no se reproduce cuando `prefers-reduced-motion: reduce`; se usa el póster.

## 6. Flujo de datos y fallos

1. Frappe entrega el login y el enlace OAuth válido.
2. `sgc_web.js` mejora progresivamente el DOM. Si JavaScript falla, el login nativo continúa
   visible y utilizable.
3. El navegador solicita las métricas agregadas con timeout de 4 segundos.
4. Respuesta válida: se pintan números y microvisualizaciones.
5. Timeout/error/dato inválido: cada cifra queda en `—`; el acceso SSO nunca se bloquea.
6. Video fallido: queda el póster; póster fallido: queda un fondo navy seguro.

El endpoint público no devuelve nombres de usuarios, programas asociados a personas, correos,
documentos, evidencias ni identificadores internos. Solo entrega los tres agregados y una marca
de tiempo de cálculo. Contrato JSON:

```json
{
  "programas": { "activos": 22, "sedes": 3 },
  "autoevaluaciones": { "activas": 6, "total": 10, "pct": 60 },
  "evidencias": { "vigentes": 84, "con_vigencia": 100, "pct": 84 },
  "calculado_en": "2026-07-20T15:00:00-05:00"
}
```

`evidencias.pct` admite `null`. La respuesta se cachea 300 segundos para evitar consultas en
cada visita.

## 6.1 Origen y destino de activos

| Activo | Fuente durante esta fase | Destino versionado en SGC |
| --- | --- | --- |
| Video provisional | `/Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti.mp4` | `sgc/public/media/login/oficinas-dti.mp4` |
| Póster provisional | `/Users/alberto/proyectos/productos/devsupeu/canonico/frontend/public/oficinas-dti-poster.jpg` | `sgc/public/media/login/oficinas-dti-poster.jpg` |
| Logo oficial blanco | `/Users/alberto/proyectos/upeu/branding/logos/2026-web/upeu-logo-2026-white.svg` | `sgc/public/media/login/upeu-logo-2026-white.svg` |

Frappe los sirve respectivamente como `/assets/sgc/media/login/oficinas-dti.mp4`,
`/assets/sgc/media/login/oficinas-dti-poster.jpg` y
`/assets/sgc/media/login/upeu-logo-2026-white.svg`. El MP4 fuente ya está optimizado (~1.5 MB,
H.264, sin audio y con faststart); la implementación verificará esas propiedades, no lo
recomprimirá a ciegas.

## 7. Accesibilidad y seguridad

- Contraste mínimo: 4.5:1 para texto y 3:1 para cromo.
- Foco visible en CTA y enlaces; navegación completa por teclado.
- Logo con texto alternativo; video decorativo fuera del árbol accesible.
- El contenido no depende solo del color.
- No se interpolan URLs OAuth ni HTML procedente de la API.
- Se conserva el `state` OAuth generado por Frappe y la política actual de redirección.
- La portada no expone datos personales ni información de seguridad operacional.

## 8. Verificación

### Automatizada

- Pruebas Python del endpoint: permisos guest, agregados correctos para cada filtro, denominador
  de evidencias en cero, cero PII, contrato JSON y cache de 300 segundos.
- Prueba DOM/JavaScript: mejora progresiva, preservación del enlace Keycloak y fallback sin API.
- Build del frontend/app sin errores.
- Verificadores de SciBack Design System 2.0.0:
  `verificar-clases-color.mjs`, `verificar-contraste.mjs` y
  `verificar-capa-institucional.mjs`, incluyendo canario negativo.

### Visual y funcional

- Capturas a 1440×1000, 834×1112 y 390×844.
- Verificación con movimiento normal y `prefers-reduced-motion`.
- Video nítido, sin blur; tarjeta visible aunque las animaciones no corran.
- Login real con Keycloak y retorno a `/sgc`; acceso local directo mediante
  `/login?login_local=1`.
- Prueba de error OAuth, video caído y endpoint de métricas caído.
- Lighthouse/axe sin errores críticos; sin scroll horizontal.

## 9. Despliegue y rollback

- Flujo: cambios locales → commit → push → `git pull` en el servidor → build/migrate/clear-cache
  según corresponda → verificación en producción.
- No se reinicia ningún servicio crítico sin aprobación previa.
- El cambio es reversible restaurando `sgc_web.css`, `sgc_web.js` y los hooks/endpoints de esta
  entrega; la autenticación de Frappe no se sustituye, por lo que el rollback no requiere
  migrar usuarios ni sesiones.

## 10. Fuera de alcance

- Rediseño de `/sgc`, páginas CRUD, tableros, Frappe Desk o páginas web heredadas.
- Implementación del selector claro/oscuro dentro de la aplicación.
- Producción de un video específico para Calidad UPeU.
- Cambios en Keycloak, Entra ID o el flujo OAuth.
