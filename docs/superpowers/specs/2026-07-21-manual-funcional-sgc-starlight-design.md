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
5. Caddy: autenticación y enrutamiento por prefijo.
6. Frappe: endpoint mínimo de autorización basado en la sesión existente.

### 4.2 Enrutamiento

El host mantiene una sola entrada TLS:

1. `/manual` responde con redirección permanente a `/manual/` sin cambiar esquema ni host.
2. `/manual/*` ejecuta una subsolicitud de autorización a Frappe conservando la cookie de
   sesión.
3. Si el usuario es `Guest`, la respuesta redirige a `/login?redirect-to=/manual/`.
4. Si la sesión es válida, Caddy elimina el prefijo `/manual` al hacer proxy al contenedor.
5. Las demás rutas continúan hacia `frontend:8080`, como en producción actualmente.

El endpoint de autorización no devuelve datos personales ni permisos del usuario. Solo comunica
si la sesión es válida. La URL de retorno debe validarse como ruta local para impedir redirecciones
abiertas.

### 4.3 Respuestas y caché

- HTML y sitemap: sin caché larga.
- Assets con hash bajo `_astro/`: `public, max-age=31536000, immutable`.
- Assets no versionados: caché corta o revalidación.
- Rutas inexistentes: estado HTTP 404 y página propia, nunca `index.html` de la SPA.
- Healthcheck: archivo estático interno que no depende de Frappe.

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

El inventario definitivo de páginas se cerrará después de extraer todos los workflows,
controladores y endpoints. No se fusionarán dos flujos si tienen actores, estados o reglas de
aprobación diferentes.

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
- UPeU: `#003366`, `#f8a900`, tintas sobre marca y activos institucionales.

La capa UPeU no redefinirá fondo, superficie, tinta, estados ni colores de gráficos. El ámbar se
usará como acento o relleno con tinta oscura; nunca como texto normal sobre una superficie clara.

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

## 8. Calidad y verificadores

### 8.1 Comprobaciones locales y CI

- frontend principal: build y pruebas existentes;
- documentación: `astro check` y build;
- enlaces internos y referencias a anchors;
- sitemap y página 404;
- contraste medido en claro y oscuro;
- búsqueda de secretos y PII prohibida;
- reglas de caché;
- imagen Docker completa del manual;
- integración Caddy + manual + aplicación simulada;
- pruebas HTTP de rutas y estados;
- pruebas responsive con navegador real;
- detección de desbordamiento horizontal.

Los verificadores críticos tendrán un canario negativo versionado: se ejecutará una fixture
deliberadamente inválida y el check solo pasará si el verificador la rechaza.

### 8.2 Matriz HTTP mínima

| Caso | Resultado esperado |
| --- | --- |
| `/` | La aplicación conserva su respuesta vigente |
| `/sgc/` | La SPA conserva su respuesta y autenticación |
| `/manual` | 308/301 a `/manual/`, conservando HTTPS |
| `/manual/` sin sesión | Redirección al login institucional |
| `/manual/` con sesión | 200 |
| Página interna con sesión | 200 |
| Ruta inexistente del manual con sesión | 404 propio |
| Asset versionado | 200 + caché immutable |
| HTML | 200 sin caché larga |

### 8.3 Verificación visual

Se revisará como mínimo a 1440 px y 390 px de ancho, en temas claro y oscuro. Las pruebas
confirmarán navegación, búsqueda, foco visible, tablas, bloques de flujo y ausencia de scroll
horizontal. Se usará el navegador para inspección real; una captura aislada no sustituye las
mediciones de DOM y contraste.

## 9. CI y despliegue

### 9.1 CI

El workflow del manual se cambiará de publicación en GitHub Pages a validación del artefacto
productivo. Debe ejecutarse cuando cambien:

- `docs-site/**`;
- configuración del contenedor o proxy;
- endpoint de autorización;
- fuentes funcionales que puedan volver obsoleto el manual, según un inventario mantenible.

CI no manejará secretos productivos. La prueba de autenticación utilizará un upstream simulado
con respuestas Guest/autenticado.

### 9.2 Producción

1. modificar y verificar localmente;
2. commit y push a GitHub;
3. `git pull` en un checkout persistente del EC2 `sgc-app`;
4. construir la imagen del manual;
5. desplegar o reemplazar solo `sgc-manual`;
6. validar la configuración de Caddy;
7. recargar Caddy en caliente;
8. ejecutar smoke tests anónimos y autenticados;
9. confirmar que los contenedores Frappe conservan estado y tiempo de actividad.

No se usará `scp`. Si fuese necesario modificar el endpoint de autorización dentro de la imagen
Frappe, ese cambio se desplegará por el flujo versionado normal y se solicitará aprobación antes
de reemplazar cualquier servicio crítico. La integración se diseñará para evitar esta sustitución
si Caddy puede validar la sesión mediante un endpoint nativo seguro ya existente.

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

El contenedor del manual es reemplazable y no comparte volúmenes de escritura con Frappe. El
rollback consiste en volver a la imagen anterior y recargar Caddy. Si la ruta se retira, Caddy
vuelve a enviar todo al frontend actual. Los servicios de datos y ejecución no requieren
migración ni rollback.

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
- existe una guía por rol y una página por flujo confirmado;
- cada flujo cumple la plantilla funcional obligatoria;
- contenido y estados coinciden con el código actual;
- los builds, enlaces, contraste, Docker e integración pasan;
- `/`, `/sgc/` y una ruta interna de la aplicación no presentan regresiones;
- `/manual` redirige, `/manual/` y una página interna responden 200 con sesión, y una ruta
  inexistente responde 404;
- escritorio y móvil no tienen desbordamiento horizontal;
- el despliegue afecta únicamente el servicio necesario para el manual y la recarga en caliente
  del proxy;
- la entrega final informa URL, ruta, páginas, roles, flujos, verificaciones, commit, estado de
  producción, limitaciones y datos/cuentas faltantes.

## 13. Fuera de alcance

- Cambiar la lógica funcional del SGC para que coincida con la documentación.
- Crear permisos o portales que no existan, incluido el portal de `Lector Externo`.
- Modificar Keycloak, Entra ID o el flujo de autenticación institucional.
- Reiniciar base de datos, Redis, workers o scheduler.
- Publicar el manual de forma anónima o mantener GitHub Pages como origen público productivo.
