# Auditoría de preparación funcional del SGC

**Fecha:** 21 de julio de 2026

**Alcance:** código canónico, interfaz SPA, datos de producción y CI

**Objetivo:** determinar qué funciona realmente y en qué orden debe terminarse el sistema antes de convertir el manual en una guía operativa.

## Conclusión ejecutiva

El SGC tiene un dominio backend amplio, 67 DocTypes y 14 workflows activos, pero todavía no constituye una experiencia operativa completa para usuarios reales. La interfaz principal es, en gran parte, un CRUD genérico: expone módulos y campos, pero no implementa las acciones de workflow que exige el proceso de negocio. Por ello, hoy no puede ejecutarse de punta a punta desde la SPA el flujo principal de autoevaluación.

El manual actual refleja la arquitectura e intención del producto, no un comportamiento validado de extremo a extremo. No debe ampliarse con instrucciones más específicas hasta que exista al menos un recorrido vertical estable, probado con sesiones de roles reales.

Los tres bloqueos principales son:

1. La SPA no ofrece las transiciones de workflow que sí existen en el backend.
2. La segregación por programa está inactiva en producción: no hay registros `User Permission` y el filtro actual permite acceso total cuando no existe asignación.
3. La suite principal de CI está roja: 305 pruebas ejecutadas, con 3 fallos y 9 errores, concentrados en cierre, inmutabilidad, snapshots y validación de estados.

## Escala de prioridad

- **P0 — bloqueante:** impide operar con usuarios reales o compromete autorización/integridad.
- **P1 — necesaria:** el flujo puede avanzar parcialmente, pero no es apto para aceptación funcional.
- **P2 — mejora:** afecta claridad, mantenibilidad o experiencia, sin bloquear el flujo base.

## Evidencia cuantitativa

| Indicador | Evidencia observada |
|---|---:|
| DocTypes definidos | 67 |
| Controladores Python de DocType | 67 |
| Controladores JavaScript de DocType | 49 |
| Archivos de pruebas de DocType | 46 |
| Páginas específicas de la SPA | 6 |
| Workflows activos en producción | 14 |
| Roles personalizados definidos | 13, además de System Manager |
| Pruebas ejecutadas en CI | 305 |
| Resultado actual de CI | 3 fallos y 9 errores |
| Programas / programas-sede en producción | 22 / 32 |
| Autoevaluaciones en producción | 1 |
| Evidencias / trazabilidades en producción | 6 / 0 |
| User Permissions en producción | 0 |

## Matriz código–interfaz–producción–pruebas

| Área | Backend actual | Interfaz actual | Producción | Cobertura comprobada | Estado / siguiente paso |
|---|---|---|---|---|---|
| Sesión y acceso | Usa la sesión de Frappe | Lee usuario, pero no carga roles ni alcance | Acceso operativo | Sin E2E por sesión real | **P1.** Exponer contexto de usuario, roles y programas permitidos |
| Roles y segregación | Matriz RBAC y filtro por Programa Sede | Menú estático igual para todos | `User Permission = 0` | Pruebas unitarias parciales | **P0.** Aprovisionar permisos y cambiar el comportamiento abierto por defecto |
| Estructura institucional | Modelos de programa, sede, facultad y marco | CRUD genérico | 22 programas, 32 programas-sede, 3 marcos y 185 elementos | Pruebas de modelos | **P1.** Validar administración con un usuario no administrador |
| Autoevaluación | Workflow de cinco estados y motor de puntaje | Vista específica, pero sin acciones de workflow | Una autoevaluación `Planificada` con avance 100% | Cierre y snapshot fallan en CI | **P0.** Implementar acciones reales y corregir invariantes de cierre |
| Valoración de criterios | Reglas de criterio y estándar | Permite editar directamente campos oficiales | 53 criterios y 10 estándares | Errores al editar después del cierre | **P0.** Impedir edición directa y usar servicios de dominio |
| Evidencia y trazabilidad | Validaciones, vigencia y proceso periódico | Consulta evidencias enlazadas; no completa el vínculo desde el recorrido | 6 evidencias, todas vencidas; 0 trazabilidades | Un fallo permite insertar estado no inicial | **P0.** Cerrar la validación de estado y completar carga/vinculación en contexto |
| Confirmación y vigencia | Métodos `confirmar_nivel`, confirmación masiva y finalización | La SPA no los invoca; edita nivel/confirmado directamente | Sin recorrido validado | Errores en confirmación y cierre | **P0.** Integrar los métodos autorizados y retirar el bypass |
| Informe y PDF | Generación y snapshot en backend | Sin recorrido completo desde la SPA | Sin evidencia de cierre exitoso | Pruebas de snapshot rojas | **P0.** Lograr cierre reproducible y artefacto inmutable |
| Plan de mejora / CAPA | Modelos, workflow y acciones | CRUD genérico | 1 plan borrador y 3 acciones en estados distintos | Scripts backend, no E2E de rol | **P1.** Probar después del flujo de autoevaluación |
| Documentos controlados | Adjuntos Frappe y workflow | CRUD genérico | 5 documentos | Cobertura de modelo | **P1.** Validar versionado, aprobación y publicación con roles separados |
| Procesos | Catálogo y relaciones | CRUD genérico | 25 procesos | Sin recorrido de usuario | **P1.** Completar el mapa institucional y validar responsables |
| Riesgos | Riesgo y tratamiento con workflows | CRUD genérico | 3 riesgos | Pruebas de backend | **P1.** Probar identificación, tratamiento y cierre por roles |
| Auditorías | Programa, auditoría, hallazgo e informe | CRUD genérico | 1 programa, 1 auditoría, 3 hallazgos y 1 informe | No hay E2E de auditor | **P1.** Construir recorrido específico de auditoría |
| Revisión por la dirección | Modelo y workflow | CRUD genérico | 1 revisión | Sin E2E de alta dirección | **P1.** Validar entradas, acuerdos y seguimiento |
| Cumplimiento | Modelo y workflow de informe | CRUD genérico | 0 informes | Fallos asociados a cierre/snapshot | **P1.** Crear caso completo después de estabilizar cierre |
| Indicadores | Modelo y tablero ejecutivo | Tablero específico | 91 valores | No se encontró colector Oracle LAMB en el repositorio canónico | **P1.** Documentar y probar el origen real de los datos |
| Encuestas | Modelo y campos de referencia | CRUD genérico | Sin integración comprobada | No se encontró sincronización LimeSurvey | **P2.** Definir si será integración real o carga manual |
| Notificaciones y tareas | Notificaciones configurables y tareas diarias de vencimiento | Sin centro de notificaciones propio | Evidencias aparecen vencidas | Sin E2E de entrega por transición | **P1.** Probar destinatarios, correo y ejecución periódica |
| Menú y búsqueda | No aplica | Todos ven todas las áreas; búsqueda marcada “próximamente” | Visible en la SPA | Sin pruebas por rol | **P1/P2.** Menú por capacidad y búsqueda funcional |
| Manual | Starlight publicado | Enlace de Inicio aún apunta a la URL histórica de GitHub Pages | `/manual/` disponible | Build del manual verde | **P2.** Actualizar el enlace y completar contenido solo con flujos validados |

## Hallazgos prioritarios

### P0-01 — La SPA no puede ejecutar workflows

El backend define, entre otras, las transiciones de autoevaluación:

`Planificada → En curso → En revisión → Consolidada → Cerrada`

La SPA no invoca `get_transitions`, `apply_workflow`, `submit` ni `cancel`. Las expresiones “Iniciar evaluación”, “Enviar a revisión”, “Consolidar”, “Aprobar” y “Publicar” aparecen en las guías de rol, pero no están implementadas como acciones de interfaz.

**Impacto:** una guía operativa basada en esos botones sería falsa.

**Aceptación:** cada transición debe estar disponible solo al rol autorizado, mostrar el estado resultante y persistir el historial.

### P0-02 — La segregación por programa está abierta por defecto

El filtro de permisos por programa es optativo: si el usuario no tiene `User Permission` para `Programa Sede`, no se restringen los registros. En producción hay cero asignaciones.

**Impacto:** incorporar usuarios funcionales sin corregir esto puede exponer datos de todos los programas.

**Aceptación:** un usuario de programa sin asignación debe ver cero registros protegidos, no todos; las cuentas de prueba deben tener asignaciones explícitas.

### P0-03 — Cierre e inmutabilidad están rotos en CI

La ejecución actual de 305 pruebas termina con 3 fallos y 9 errores. Los fallos afectan creación/edición después del cierre, confirmación, cierre nativo, snapshots y estados iniciales de evidencia.

**Impacto:** no es posible confiar en puntajes, informes ni congelamiento de datos cerrados.

**Aceptación:** suite completa verde y una prueba de regresión que demuestre que un documento cerrado ya no puede modificarse.

### P0-04 — La interfaz permite saltarse servicios de dominio

La pantalla de detalle modifica directamente estado, nivel oficial, confirmación y justificación. El backend ya tiene funciones específicas para confirmar y finalizar vigencias, pero la SPA no las usa.

**Impacto:** pueden aparecer combinaciones de estado inválidas, como la autoevaluación de producción `Planificada` con avance 100%.

**Aceptación:** los campos derivados/oficiales deben ser de solo lectura; los cambios deben pasar por comandos de dominio auditables.

### P1-01 — Producción contiene una muestra, no un caso representativo

Hay una sola autoevaluación para 32 programas-sede. Sus seis evidencias son demo y están vencidas; no existe ninguna trazabilidad. También faltan informes de cumplimiento.

**Impacto:** el sistema no ha demostrado el flujo con datos representativos.

**Aceptación:** crear un conjunto de prueba aislado, vigente y trazable para un programa piloto.

### P1-02 — Los scripts llamados E2E no simulan usuarios reales

Los scripts de fases F2/F3 crean y mutan documentos con `ignore_permissions=True` y banderas de patch. Verifican lógica backend, pero no sesión, menú, permisos, workflow ni navegación.

**Impacto:** pueden pasar aunque un usuario real no pueda completar ninguna tarea.

**Aceptación:** pruebas de navegador con cuentas reales, permisos reales y sin bypass de autorización.

## Primer recorrido que debe terminarse

La prioridad no es completar todos los módulos. Es cerrar un único recorrido de acreditación de extremo a extremo:

1. Un administrador prepara estructura, marco, periodo y programa-sede.
2. DPGC crea una autoevaluación en estado `Planificada`.
3. RPRO inicia la evaluación y pasa a `En curso`.
4. RPRO valora criterios y estándares, adjunta evidencia vigente y crea la trazabilidad.
5. RPRO envía a revisión.
6. DPGC devuelve con observaciones o consolida.
7. Un segundo usuario autorizado cierra la autoevaluación, respetando la separación de aprobación.
8. El sistema congela datos, conserva el cálculo y genera el informe/PDF.
9. Un usuario sin permiso para ese programa no puede verlo ni abrirlo por URL directa.

Cuando este recorrido esté verde, el manual podrá describirlo con pasos y capturas reales.

## Backlog inicial propuesto

| Orden | Trabajo | Criterio de terminado |
|---:|---|---|
| 1 | Corregir los 12 errores/fallos actuales de CI | 305 pruebas verdes |
| 2 | Implementar componente común de acciones de workflow | Transiciones visibles y autorizadas en SPA |
| 3 | Retirar edición directa de estado, nivel oficial y confirmación | Campos derivados de solo lectura |
| 4 | Cambiar permisos de programa a cerrado por defecto | Sin asignación se ven cero registros protegidos |
| 5 | Cargar contexto de roles y alcance en la sesión SPA | Menú y acciones dependen de capacidades reales |
| 6 | Crear usuarios y datos del piloto | Cuentas con permisos explícitos y evidencia vigente |
| 7 | Completar evidencia y trazabilidad dentro del detalle | RPRO no necesita entrar a CRUD genéricos |
| 8 | Estabilizar cierre, snapshot e informe | PDF y datos cerrados reproducibles e inmutables |
| 9 | Añadir E2E de navegador para tres roles | Flujo principal y casos negativos automatizados |
| 10 | Reescribir la sección operativa del manual | Cada paso coincide con UI y pruebas verdes |

## Cuentas y datos necesarios

Para completar el primer E2E hacen falta, como mínimo:

- una cuenta de administración funcional;
- una cuenta RPRO asignada únicamente al programa piloto;
- dos cuentas DPGC si se conserva la prohibición de autoaprobación;
- un programa-sede piloto con periodo vigente;
- marco y elementos aplicables al programa;
- seis a diez evidencias no sensibles, vigentes y aptas para prueba;
- un sitio o conjunto de datos de prueba que pueda reiniciarse sin alterar registros reales.

Para la segunda etapa serán necesarias cuentas de Auditor, Responsable de Auditoría, Dueño de Proceso y Alta Dirección.

## Decisión recomendada

No intentar “llenar” todo el manual todavía. Primero completar los trabajos 1 al 9 del backlog para el recorrido de autoevaluación. Después, convertir ese recorrido validado en la primera sección funcional real del manual y repetir el patrón módulo por módulo.

## Fuentes revisadas

- Arquitectura indexada del repositorio canónico mediante codebase-memory.
- Rutas, páginas, componentes y stores de `frontend/src/`.
- Workflows, RBAC, permisos, scoring, confirmación, tareas programadas y pruebas de `sgc/`.
- Estado de la rama `main` y ejecución CI vigente en GitHub Actions.
- Conteos, workflows y estados observados de forma no destructiva en producción el 21 de julio de 2026.

No se publicaron contraseñas, tokens, DNI, correos personales ni otros secretos en este informe.
