# Diseño: manual funcional protegido de SGC UPeU con Astro + Starlight

**Fecha:** 2026-07-21  
**Estado:** aprobado por Alberto para especificación  
**Sistema:** `https://calidad.upeu.edu.pe/`  
**URL canónica del manual:** `https://calidad.upeu.edu.pe/manual/`

## 1. Objetivo

Convertir el `docs-site/` existente en el manual funcional verificable de SGC UPeU. Debe
permitir que una persona nueva entienda el sistema, lo pruebe de punta a punta con cada rol
real, ejecute una regresión y reporte hallazgos con evidencia útil.

La documentación se derivará del código vigente. No se presentará como disponible ninguna
función que solo exista como modelo, roadmap o intención. Las dependencias operativas, cuentas,
configuración y datos que impidan completar una prueba se señalarán de forma explícita.

## 2. Situación encontrada

El repositorio ya contiene un sitio Astro + Starlight en `docs-site/`, con 21 páginas sobre
arquitectura, módulos y algunos flujos. Actualmente:

- usa `base: '/sgc'` y publica mediante GitHub Pages;
- mezcla documentación de producto, desarrollo y uso;
- no contiene una guía independiente para cada rol;
- no ofrece una regresión funcional completa;
- no está integrado en el despliegue productivo de `calidad.upeu.edu.pe`;
- no está protegido por la sesión institucional del SGC.

El contenido existente se conservará únicamente cuando coincida con el código actual. Cada
afirmación funcional se contrastará con rutas, controladores, servicios, DocTypes, workflows,
RBAC, tareas periódicas, reportes y pruebas.

## 3. Decisiones aprobadas

- URL pública estable: `/manual/` en el mismo host del SGC.
- Astro: salida estática y `base: '/manual'`.
- Acceso: misma sesión Frappe autenticada mediante Keycloak/Microsoft 365.
- Despliegue: contenedor estático independiente `sgc-manual`.
- Proxy: Caddy enruta solo `/manual` y `/manual/*`; el resto continúa hacia Frappe.
- No se reinician backend, PostgreSQL, Redis, colas ni scheduler para publicar documentación.
- El sitio existente se reestructura; no se crea un segundo manual paralelo.
- SciBack define el sistema visual; UPeU aporta únicamente marca y activos institucionales.
- No se copia un logotipo si no hay necesidad funcional; se prefiere marca textual o una fuente
  institucional oficial y estable.

## 4. Arquitectura de ejecución

### 4.1 Componentes

1. `docs-site/`: fuente Astro + Starlight y contenido Markdown/MDX.
2. `docs-site/Dockerfile`: build multi-stage reproducible y servidor estático mínimo.
3. Configuración del servidor estático: 404 real, cabeceras y caché selectiva.
4. `sgc-manual`: contenedor independiente conectado a la red externa `sgc-proxy`.
5. Caddy: autenticación y enrutamiento por prefijo; conectado de forma declarativa a
   `sgc-proxy` y `sgc-prod-net`.
6. Frappe: endpoint mínimo `sgc.manual_auth.authorize`, basado en la sesión existente.

La topología productiva comprobada el 2026-07-21 es: `sgc-caddy` está conectado a
`sgc-proxy` y `sgc-prod-net`; `frappe-prod-frontend-1` está en `sgc-prod-net` con alias
`frontend`. Esa conexión no seguirá siendo un ajuste manual: el Compose versionado de Caddy
declarará ambas redes externas y el Compose del manual declarará `sgc-proxy`.

### 4.2 Enrutamiento

El host mantiene una sola entrada TLS:

1. `/manual` responde con redirección permanente a `/manual/` sin cambiar esquema ni host.
2. `/manual/*` ejecuta una subsolicitud `GET` a
   `/api/method/sgc.manual_auth.authorize`, conservando la cookie de sesión solo hacia Frappe.
3. El contrato exacto del endpoint es: sesión válida `204`; `Guest`, sesión expirada o revocada
   `302` con `Location: /login?redirect-to=/manual/`; error interno `5xx`.
4. Si la sesión es válida, Caddy elimina el prefijo `/manual` al hacer proxy al contenedor.
5. Las demás rutas continúan hacia `frontend:8080`, como en producción actualmente.

El endpoint usa `frappe.session.user`, nunca las cookies auxiliares `user_id`, `full_name` o
`system_user`. No recibe una URL de retorno arbitraria: la redirección es fija y local. Responde
siempre con `Cache-Control: private, no-store`; no devuelve identidad, roles ni datos personales.
Los `5xx` fallan cerrados y nunca habilitan el manual.

Después de autorizar, Caddy elimina `Cookie`, `Authorization`, cabeceras `X-Frappe-*` y cualquier
cabecera de identidad antes del proxy a `sgc-manual`. El servidor estático no registra cookies ni
puede alcanzar `sgc-prod-net`.

### 4.3 Respuestas y caché

- HTML, 404, sitemap, manifiestos e índices de búsqueda/Pagefind:
  `private, no-store`.
- Assets con hash bajo `_astro/`: `private, max-age=31536000, immutable`.
- Assets no versionados: `private, no-cache`.
- Rutas inexistentes: estado HTTP 404 y página propia, nunca `index.html` de la SPA.
- Healthcheck: archivo estático interno que no depende de Frappe.

El servidor estático será `nginxinc/nginx-unprivileged:1.28-alpine`, fijado además por digest al
implementar; el build usará `node:24-alpine`, también fijado por digest, y `npm ci` sobre el
lockfile. La resolución será exactamente `archivo` → `directorio/index.html` → `=404`, con
`error_page 404 /404.html` conservando el estado 404. No existe fallback a `index.html`.

## 5. Arquitectura de información

La navegación funcional tendrá estas áreas:

1. **Inicio**: propósito, alcance, estado real y entrada rápida a pruebas.
2. **Mapa del sistema**: módulos, relaciones y conceptos.
3. **Preparación**: acceso, datos, cuentas, precondiciones y entorno.
4. **Roles y permisos**: matriz general y una guía independiente por rol.
5. **Flujos funcionales**: una página por flujo confirmado en el código.
6. **Reglas de negocio**: estados, transiciones, scoring, vigencias y restricciones.
7. **Prueba E2E**: recorrido principal de principio a fin.
8. **Regresión**: checklist ejecutable por módulo y rol.
9. **Hallazgos**: cómo reproducir, capturar y reportar evidencia.
10. **Administración**: catálogos, RBAC, configuración y tareas periódicas.
11. **Reportes y auditoría**: PDF, Excel, historial y trazabilidad.
12. **Referencia técnica**: arquitectura, endpoints, desarrollo y pruebas automatizadas.

### 5.1 Guías por rol

Se generará una guía independiente para cada rol definido en `sgc/setup/f3b_rbac.py`, incluidos
los roles de lectura y administración. Cada guía explicará:

- propósito y alcance;
- menús y destinos realmente accesibles;
- acciones permitidas y prohibidas;
- datos que puede ver según DocPerm y User Permission;
- tareas principales;
- puntos de entrega a otro rol;
- cuenta y datos necesarios para probarlo;
- limitaciones confirmadas.

`Lector Externo` se documentará como no ejecutable mientras el código no le otorgue permisos ni
un portal acotado. `System Manager` se documentará como rol administrativo, incluyendo sus
restricciones deliberadas dentro de la matriz SGC.

El inventario cerrado inicial contiene 14 guías:

1. DPGC;
2. Analista de Calidad (DPGC);
3. Coordinador de Calidad de Facultad;
4. Responsable de Calidad de Programa;
5. Miembro de Comité de Calidad;
6. Dueño de Proceso;
7. Data Steward;
8. Auditor Interno;
9. Rectorado/VR (lectura);
10. Decano/Director (lectura);
11. Responsable de Sede;
12. Lector Externo;
13. Autoridad Aprobadora;
14. System Manager.

`docs-site/src/data/coverage.json` será el manifiesto versionado de cobertura. Para cada rol y
flujo registrará `id`, `kind`, `page`, `sources` y `status`. CI rechazará IDs o páginas duplicadas,
páginas ausentes, fuentes inexistentes y fuentes funcionales sin cobertura declarada.

El inventario inicial de workflows contiene los 14 definidos actualmente en `sgc/setup/`:
Autoevaluación, No Conformidad, Plan de Mejora, Acción de Mejora, Documento Controlado, Programa
de Auditoría, Auditoría, Aplicación de Instrumento, Revisión por la Dirección, Informe de
Cumplimiento CBC, Hallazgo, Evidencia, Riesgo y Tratamiento de Riesgo. Los flujos sin Workflow
nativo —por ejemplo trazabilidad, scoring/confirmación, indicadores, gobierno, procesos,
obligaciones, reportes y tareas periódicas— tendrán también entradas propias si el análisis de
controladores confirma acciones funcionales independientes.

### 5.2 Plantilla obligatoria de flujo

Cada flujo funcional incluirá:

1. quién puede ejecutarlo;
2. precondiciones;
3. datos y cuentas necesarios;
4. pasos numerados;
5. resultado esperado después de cada paso;
6. estados y transiciones;
7. permisos y segregación de funciones;
8. validaciones y restricciones;
9. casos negativos;
10. evidencia que debe capturarse;
11. notificaciones o procesos periódicos relacionados;
12. relación con otros módulos;
13. fuente de verdad en el código.

El manifiesto se completará antes de escribir las páginas y será el inventario definitivo. No se
fusionarán dos flujos si tienen actores, estados o reglas de aprobación diferentes.

## 6. Investigación y trazabilidad

La investigación seguirá este orden:

1. instrucciones del repositorio, README y documentación enlazada;
2. arquitectura e inventario mediante `codebase-memory`;
3. archivos concretos señalados por el grafo;
4. rutas y menús frontend;
5. DocTypes, controladores y servicios backend;
6. matriz RBAC, permlevels, User Permission y condiciones programáticas;
7. workflows, estados, transiciones y `allow_self_approval`;
8. validaciones, cálculo, notificaciones, scheduler y reportes;
9. pruebas automatizadas como evidencia adicional;
10. contraste con el runtime productivo solo para configuración y disponibilidad.

Cada página mantendrá una sección de trazabilidad interna o metadatos de mantenimiento con los
archivos fuente relevantes. No se publicarán rutas sensibles, credenciales, identificadores
personales ni datos reales.

## 7. Diseño visual

### 7.1 Capas

- SciBack: tipografía, escala, espaciado, radios, neutros, superficies, estados, componentes y
  movimiento.
- La implementación UPeU: `#003366`, `#f8a900`, tintas sobre marca y activos institucionales.

La capa UPeU no redefinirá fondo, superficie, tinta, estados ni colores de gráficos. El ámbar se
usará como acento o relleno con tinta oscura; nunca como texto normal sobre una superficie clara.

La separación será física y entre repositorios:

- producto canónico: `/Users/alberto/proyectos/productos/sgc/canonico/docs-site/` y checkout
  productivo `/opt/sgc/src/sgc/docs-site/`; contiene contenido funcional, estilos SciBack
  neutrales y un punto de extensión institucional genérico;
- overlay UPeU: `/Users/alberto/proyectos/upeu/upeu-ops/services/sgc/manual/` en el repo
  `UPeU-Infra/upeu-ops`, y checkout productivo `/opt/sgc/upeu-ops/services/sgc/manual/`; contiene
  `institution.css`, Compose, plantilla Caddy y parámetros del host.

El Dockerfile final del overlay usa contextos BuildKit con nombre (`canonical` y `overlay`):
construye el `docs-site/` canónico y copia `institution.css` dentro de la imagen final. Así el
digest identifica contenido y marca juntos; no queda CSS mutable montado desde el host. El overlay
no modifica el manual. `docs-site/` no contendrá tokens, cuentas, datos, activos ni configuración
de despliegue UPeU.

### 7.2 Experiencia

- Starlight conserva búsqueda, navegación responsive, índice, foco y temas claro/oscuro.
- La portada prioriza “comenzar una prueba” y “probar por rol”.
- Componentes reutilizables: ficha de rol, matriz de permisos, secuencia de estados, paso de
  prueba, resultado esperado, caso negativo, evidencia requerida, advertencia y limitación.
- Interacciones habituales sin animación ornamental.
- Pulsables con feedback sutil; transiciones menores de 300 ms y propiedades concretas.
- `prefers-reduced-motion` conserva comprensión sin desplazamientos innecesarios.
- Zonas táctiles de al menos 44×44 px.
- Contraste mínimo: 4.5:1 para texto y 3:1 para cromo/controles en claro y oscuro.

### 7.3 Configuración Astro

- `site` parametrizado por `DOCS_SITE` y obligatorio en build productivo;
- `base` parametrizado por `DOCS_BASE`, con valor canónico `/manual`;
- salida estática;
- sitemap habilitado para el host y base nuevos;
- búsqueda local de Starlight;
- enlaces internos sin prefijos escritos a mano;
- eliminación de canónicas, enlaces de edición y referencias de salida a
  `sciback.github.io/sgc` o `/sgc`.

CI canónico construirá con un host de prueba no institucional; el overlay productivo construirá
con `DOCS_SITE=https://calidad.upeu.edu.pe` y `DOCS_BASE=/manual`. Ambos inspeccionarán `dist/` y
fallarán ante referencias a los hosts/prefijos anteriores.

## 8. Calidad y verificadores

### 8.1 Comprobaciones locales y CI

- frontend principal: `npm ci`, `npm run build`, `npm run test:login-dom` y verificadores
  existentes;
- documentación: `npm run check` (`astro check`) y `npm run build`;
- `npm run verify:links`: script Node que resuelve páginas, assets y anchors desde `dist/`;
- `npm run verify:coverage`: valida `src/data/coverage.json`, páginas y fuentes;
- `npm run verify:privacy`: patrones prohibidos de secretos, DNI, correos personales y fixtures
  conocidas sobre fuente y artefacto;
- `npm run verify:contrast`: Playwright + axe-core en claro y oscuro;
- `npm run verify:dist`: sitemap, 404, host/base, búsqueda y ausencia del host/prefijo anterior;
- `npm run verify:docker`: build de imagen por SHA y prueba de Nginx/headers;
- `npm run verify:integration`: Compose efímero con Caddy, upstream Frappe simulado y manual;
- `npm run verify:visual`: Playwright a 1440 y 390 px, temas claro/oscuro y
  `scrollWidth <= clientWidth`.

En `docs-site/tests/fixtures/` habrá casos deliberadamente inválidos para enlaces, cobertura,
PII, contraste y configuración de caché/base. Cada canario solo pasa si su verificador termina
con código distinto de cero. El workflow ejecutará explícitamente los cinco canarios.

### 8.2 Matriz HTTP mínima

| Caso | Resultado esperado |
| --- | --- |
| `/` | Conserva el código y `Location` vigentes |
| `/sgc/` | Conserva su respuesta y autenticación |
| `/manual` | 308 a `https://calidad.upeu.edu.pe/manual/` |
| `/manual/` sin sesión | 302 a `/login?redirect-to=/manual/` |
| `/manual/` con sesión | 200 |
| Página interna con sesión | 200 |
| Ruta inexistente del manual con sesión | 404 propio |
| Asset `_astro` versionado | 200 + `private, max-age=31536000, immutable` |
| HTML, sitemap, 404 e índice de búsqueda | `private, no-store` |
| `/manualfoo` | Continúa hacia Frappe; no entra al manual |
| `HEAD` de página válida/inexistente | Mismo estado y cabeceras que GET, sin cuerpo |
| Frappe de autorización en `5xx` | Manual no servido; respuesta cerrada |

Las pruebas de autorización incluyen sesión válida, expirada, revocada y cookie `user_id`
falsificada sin `sid` válido.

### 8.3 Verificación visual

Se revisará como mínimo a 1440 px y 390 px de ancho, en temas claro y oscuro. Las pruebas
confirmarán navegación, búsqueda, foco visible, tablas, bloques de flujo y ausencia de scroll
horizontal. Se usará el navegador para inspección real; una captura aislada no sustituye las
mediciones de DOM y contraste.

El contenedor añadirá `X-Content-Type-Options: nosniff`, `Referrer-Policy: same-origin`, una
política de framing `SAMEORIGIN`/`frame-ancestors 'self'` y una CSP compatible con el build real
de Starlight. CI comprobará que la CSP no bloquea CSS, búsqueda ni scripts propios.

## 9. CI y despliegue

### 9.1 CI

El workflow del manual se cambiará de publicación en GitHub Pages a validación del artefacto
productivo. Debe ejecutarse cuando cambien:

- `docs-site/**`;
- `sgc/manual_auth.py` y sus pruebas;
- `frontend/src/router.js`, `frontend/src/layouts/**`, `frontend/src/pages/**`;
- `sgc/hooks.py`, `sgc/scoring.py`, `sgc/confirmacion.py`, `sgc/capa.py`, `sgc/informe.py`,
  `sgc/lista_maestra.py`, `sgc/tasks.py`, `sgc/permissions.py`;
- `sgc/setup/f*_workflow*.py`, `sgc/setup/f3b_rbac.py`;
- `sgc/sgc_*/doctype/**`.

El repo cliente `UPeU-Infra/upeu-ops` tendrá su propio workflow para
`services/sgc/manual/**`; comprobará el overlay, construirá el manual canónico con los parámetros
UPeU y ejecutará la integración completa Caddy + autenticación simulada + contenedor.

CI no manejará secretos productivos. La prueba de autenticación utilizará un upstream simulado
con respuestas Guest, autenticado y `5xx`. `.github/workflows/docs.yml` perderá permisos y pasos
de GitHub Pages; solo validará y publicará como artefacto temporal el `dist/` y los reportes.

Antes de publicar el nuevo contenido protegido se deshabilitará GitHub Pages mediante la API de
GitHub (`DELETE /repos/SciBack/sgc/pages`) y se verificará que la URL anterior ya no expone el
manual. Retirar el workflow no cuenta como despublicación.

### 9.2 Producción

El primer despliegue tiene dos fases explícitas:

**Habilitación inicial de autorización (una sola vez):** desplegar `sgc/manual_auth.py` y su
prueba dentro de la imagen Frappe, con aprobación previa para reemplazar únicamente el servicio
`frappe-prod-backend-1` mediante `docker compose up -d --no-deps backend`. Frontend, websocket,
scheduler, workers, Redis y PostgreSQL no se reemplazan. Se captura estado y uptime, se prueba el
contrato 204/302/5xx y se conserva el tag/digest backend anterior para rollback. Esta fase no se
presenta como una publicación ordinaria del manual.

**Manual y proxy:**

1. modificar y verificar localmente;
2. commit y push a GitHub;
3. `git pull` en los checkouts persistentes `/opt/sgc/src/sgc` y `/opt/sgc/upeu-ops` del EC2
   `sgc-app`;
4. construir `sgc-manual:<canonical-short-sha>-<overlay-short-sha>` con ambos contextos y
   registrar `CANONICAL_SHA`, `OVERLAY_SHA`, digest y nombre de contenedor;
5. iniciar un contenedor candidato
   `sgc-manual-<canonical-short-sha>-<overlay-short-sha>` sin modificar todavía el upstream
   activo y esperar estado `healthy`;
6. guardar el release activo y el Caddyfile vigente;
7. generar el Caddyfile candidato apuntando al nombre exacto del contenedor saludable y ejecutar
   `caddy validate`;
8. recargar Caddy en caliente y ejecutar smoke tests anónimos y autenticados;
9. solo si pasan los smoke tests, promover el candidato cambiando un único puntero atómico
   `current` al directorio inmutable del release y detener el contenedor anterior; si fallan,
   restaurar Caddy y retirar el candidato;
10. confirmar que los contenedores Frappe conservan estado y tiempo de actividad.

No se usará `scp`. Las publicaciones posteriores de contenido o estilo no reconstruyen Frappe:
solo reemplazan `sgc-manual` y recargan Caddy.

El smoke autenticado usará un script Playwright que lee credenciales desde variables de entorno
ya existentes, crea la sesión mediante la API de login, mantiene cookies solo en memoria y nunca
imprime identidad, contraseña ni `sid`. Si el login local no está habilitado, se ejecutará una
sesión interactiva SSO. No se pasan secretos por argumentos, no se escribe `storageState` y el
contexto del navegador se destruye al terminar.

## 10. Seguridad y privacidad

- El manual requiere una sesión institucional válida.
- La autorización no se basa solo en la existencia de una cookie; valida la sesión con Frappe.
- No se publican contraseñas, tokens, DNI, correos personales, nombres de cuentas reales ni
  datos de producción.
- Los ejemplos usan identificadores ficticios.
- Los parámetros de redirección se restringen a rutas locales.
- Los logs del contenedor no registran cookies ni cabeceras de autorización.
- El contenido no revela direcciones internas, secretos operativos ni configuración privada.

## 11. Operación y rollback

El contenedor del manual es reemplazable y no comparte volúmenes de escritura con Frappe. Las
imágenes usan tags inmutables por commit, nunca `latest`; el Compose productivo vive en
`/opt/sgc/upeu-ops/services/sgc/manual/`. Cada release tiene un directorio inmutable
`/opt/sgc/manual/releases/<canonical-sha>-<overlay-sha>/` cuyo `release.env` guarda
`CANONICAL_SHA`, `OVERLAY_SHA`, `IMAGE_DIGEST`, `CONTAINER_NAME` y `PREVIOUS_RELEASE_ID`.

El único estado mutable es el symlink `/opt/sgc/manual/current`. La promoción crea
`current.new` y ejecuta un único `rename` atómico sobre `current`; si el proceso cae antes, el
release anterior sigue activo. El release nuevo conserva el ID anterior en
`PREVIOUS_RELEASE_ID`, por lo que no hace falta coordinar un segundo puntero. La configuración
fuente está versionada en `UPeU-Infra/upeu-ops`; antes de cada recarga se respalda el Caddyfile
vigente con timestamp y ambos commits.

Rollback del manual: leer `PREVIOUS_RELEASE_ID` del release vigente, arrancar el
`CONTAINER_NAME` exacto de ese release con su digest, esperar `healthy`, regenerar y validar Caddy
hacia ese nombre, recargar, repetir la matriz HTTP y finalmente mover `current` con un único
rename atómico. Si el contenedor no queda saludable, se retira el handler `/manual*` y el resto
del host continúa hacia Frappe.

Rollback de la habilitación de autorización: restaurar el tag/digest Frappe anterior y su
Compose, reemplazar exclusivamente `backend` mediante
`docker compose up -d --no-deps backend` con aprobación, validar login y `/sgc/`, y retirar
temporalmente la ruta del manual. Los servicios de datos no requieren migración.

Antes y después del despliegue se registrará:

- commit desplegado;
- digest/tag de imagen;
- estado y uptime de servicios;
- matriz HTTP;
- resultados de build, links, contraste y visual;
- limitaciones y cuentas/datos de prueba faltantes.

## 12. Criterios de aceptación

La entrega se considera completa cuando:

- el manual está disponible exactamente en `https://calidad.upeu.edu.pe/manual/`;
- solo usuarios autenticados pueden leerlo;
- GitHub Pages anterior está despublicado y ya no expone el contenido;
- existe una guía por rol y una página por flujo confirmado;
- el manifiesto de cobertura valida los 14 roles, los 14 workflows y los flujos programáticos;
- cada flujo cumple la plantilla funcional obligatoria;
- contenido y estados coinciden con el código actual;
- los builds, enlaces, contraste, Docker e integración pasan;
- `/`, `/sgc/` y una ruta interna de la aplicación no presentan regresiones;
- `/manual` redirige, `/manual/` y una página interna responden 200 con sesión, y una ruta
  inexistente responde 404;
- escritorio y móvil no tienen desbordamiento horizontal;
- la habilitación inicial reemplaza únicamente `frappe-prod-backend-1` con aprobación; las
  publicaciones ordinarias afectan solo un contenedor candidato del manual y la recarga en
  caliente del proxy;
- la entrega final informa URL, ruta, páginas, roles, flujos, verificaciones, commit, estado de
  producción, limitaciones y datos/cuentas faltantes.

## 13. Fuera de alcance

- Cambiar la lógica funcional del SGC para que coincida con la documentación.
- Crear permisos o portales que no existan, incluido el portal de `Lector Externo`.
- Modificar Keycloak, Entra ID o el flujo de autenticación institucional.
- Reiniciar base de datos, Redis, workers o scheduler.
- Publicar el manual de forma anónima o mantener GitHub Pages como origen público productivo.
