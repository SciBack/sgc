# Por qué el SGC va sobre Frappe y no sobre ERPNext

Evaluación hecha el **2026-10-21** contra el **código de ERPNext 16.52.0** (tag
[`v16.52.0`](https://github.com/frappe/erpnext/tree/v16.52.0), commit `90cb7f9`, la misma versión
de Frappe que usa el SGC) y su documentación oficial. Cada afirmación cita el fichero o la página
de la que sale; conviene revalidarlas antes de volver a tomar la decisión, sobre todo la de
PostgreSQL, que está cambiando.

## La pregunta

ERPNext y el SGC están hechos sobre el mismo framework. ERPNext ya trae un módulo de **Gestión de
la Calidad** y, al ser un ERP, cualquier cosa que le falte se le puede añadir. ¿Por qué el SGC es
una app de Frappe propia en lugar de una extensión de ERPNext?

## Decisión

1. **El SGC es una app de Frappe que no depende de ERPNext.** No se instala ERPNext ni se
   extienden sus pantallas de calidad.
2. **La interfaz es la misma.** Portadas, listas, formularios, árbol, flujos de aprobación,
   cifras y gráficos, «Asignar a», avisos, formatos de impresión y portal son de **Frappe**, no de
   ERPNext; el SGC los usa (ver [`nativo-frappe.md`](../desarrollo/nativo-frappe.md)).
3. **Revisar la decisión** si una institución ya tiene ERPNext en producción, o cuando ERPNext
   publique una versión estable con PostgreSQL soportado (ver más abajo). Si el SGC necesitara
   datos de un ERPNext existente (personal, activos, proyectos), se integra por su API REST, no
   instalándolo en el mismo sitio.

## Lo que se comprobó

### 1. El módulo de calidad de ERPNext es pequeño y está pensado para producto

[`erpnext/quality_management/doctype/`](https://github.com/frappe/erpnext/tree/v16.52.0/erpnext/quality_management/doctype)
tiene **7 pantallas** y 9 tablas hijas, con unas **1.200 líneas de Python** entre todas:

| Pantalla de ERPNext | Lo que guarda | En el SGC |
|---|---|---|
| Quality Goal | Objetivo con frecuencia y objetivos medibles (`target`, `uom`) | Objetivo de calidad, Indicador y Ficha de indicador, con meta, semáforo, análisis por periodo y alertas |
| Quality Procedure | Árbol de procedimientos con dueño | Proceso (mapa N0–N2), Procedimiento con flujo de aprobación y BPMN, Ficha de caracterización (ISO 9001 §4.4.1) |
| Quality Review | Revisión de objetivos: Open / Passed / Failed | Revisión por la dirección (entradas y salidas ISO 9001 §9.3), autoevaluación contra marcos |
| Quality Action | Acción correctiva o preventiva con resoluciones | Acción de mejora con tareas, causa que ataca y verificación de eficacia |
| Quality Feedback | Encuesta de 1 a 5 a un usuario o cliente | Instrumentos, aplicaciones y resultados de encuestas por grupo de interés |
| Quality Meeting | Agenda y acta | Comité, reunión y acuerdos con responsable y plazo |
| Non Conformance | Asunto, procedimiento, estado y dos textos (correctiva, preventiva) | No conformidad con análisis de causa por metodología, segregación de funciones y cierre sellado |

Detalles del código que pesan:

- **No hay flujos de aprobación ni avisos.** El módulo no trae ningún Workflow ni Notification;
  los estados son un `Select` que se cambia a mano
  ([`non_conformance.json`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/quality_management/doctype/non_conformance/non_conformance.json):
  `Open`, `Resolved`, `Cancelled`).
- **Un solo automatismo:** la tarea programada `quality_review.review`
  ([`hooks.py:505`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/hooks.py#L505)) crea
  revisiones según la frecuencia del objetivo. Y **un solo informe**, `review`.
- **El dueño del proceso en la no conformidad es texto copiado**, no un enlace a un usuario
  (`process_owner`, `fetch_from: procedure.process_owner`): no sirve para avisar ni para segregar.
- **Depende de otros módulos del ERP:** los objetivos usan `UOM`, del módulo de Inventario
  ([`quality_goal_objective.json:29`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/quality_management/doctype/quality_goal_objective/quality_goal_objective.json#L29)).

La [documentación oficial del módulo](https://docs.frappe.io/erpnext/user/manual/en/quality-management)
lo presenta como calidad de **producto**: controles de calidad, plantillas de inspección,
no conformidades, trazabilidad por lotes, calidad de proveedores e informes. No menciona ISO,
control documental, versiones, aprobaciones, auditorías ni riesgos.

En el SGC, en cambio, hay **94 pantallas, 20 flujos de aprobación y 9 informes** (`sgc/*/doctype`,
`sgc/fixtures/workflow.json`, `sgc/*/report`), además de lo que ERPNext no tiene en absoluto:
control documental con versiones y lista maestra, marcos normativos y autoevaluación, programa,
listas de verificación e informe de auditoría (ISO 19011), riesgos y eventos de riesgo, salidas no
conformes (ISO 9001 §8.7) y la verificación de instancia.

**Conclusión del punto:** extender ERPNext para llegar al SGC significa reemplazar casi todos los
campos y toda la lógica de esas 7 pantallas. Se conservaría el nombre de la pantalla, no el
trabajo.

### 2. Instalar ERPNext trae un ERP entero

- **529 pantallas en 21 módulos** ([`modules.txt`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/modules.txt):
  Contabilidad, CRM, Compras, Ventas, Inventario, Fabricación, Activos…). Aparecen en el menú de
  todos los usuarios salvo que se oculten una a una.
- **El asistente de instalación crea la empresa, el año fiscal y el plan de cuentas**
  ([`hooks.py:90`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/hooks.py#L90),
  [`company_setup.py:8`](https://github.com/frappe/erpnext/blob/v16.52.0/erpnext/setup/setup_wizard/operations/company_setup.py#L8)).
  Una oficina de calidad no lleva contabilidad, y la institución ya tiene su sistema financiero.
- **Cada actualización de Frappe tendría que esperar a la de ERPNext** y migrar sus 529 pantallas,
  en contra de la regla de que el SGC se actualice con un `migrate`
  ([`nativo-frappe.md`](../desarrollo/nativo-frappe.md)).

### 3. ERPNext 16 no soporta PostgreSQL oficialmente, y el SGC corre sobre PostgreSQL

- El trabajo de compatibilidad se hizo en la rama **`develop`** (la futura v17): el issue
  [frappe/erpnext#24389](https://github.com/frappe/erpnext/issues/24389) se cerró el 21-jun-2026
  con el PR [#56243](https://github.com/frappe/erpnext/pull/56243), que apunta a `develop`; el PR
  grande de compatibilidad, [#55905](https://github.com/frappe/erpnext/pull/55905), se cerró sin
  fusionarse.
- En `version-16` solo hay **arreglos sueltos portados** (por ejemplo `fe6534b8`, «port
  point_of_sale get_items to the query builder (partial backport #56153)»).
- **Las pruebas sobre PostgreSQL son opcionales:** solo corren en los PR con la etiqueta
  `postgres`
  ([`server-tests-postgres.yml:23`](https://github.com/frappe/erpnext/blob/v16.52.0/.github/workflows/server-tests-postgres.yml#L23));
  las de MariaDB corren siempre
  ([`server-tests-mariadb.yml`](https://github.com/frappe/erpnext/blob/v16.52.0/.github/workflows/server-tests-mariadb.yml)).

Usar ERPNext 16 obligaría a pasar el SGC a MariaDB o a correr un ERP en un motor que su propio
proyecto no prueba en cada cambio.

### 4. Lo aprovechable de ERPNext ya viene de Frappe

De lo que ERPNext anuncia, lo que le sirve a un sistema de calidad —indicadores en tableros,
asignar tareas y hacer seguimiento, publicar en la web— **no es de ERPNext**: son las cifras y
gráficos, el `ToDo` y el portal de Frappe, que el SGC ya usa.

## Cómo revalidar

```bash
git clone --depth 1 --branch version-16 https://github.com/frappe/erpnext.git
ls erpnext/erpnext/quality_management/doctype/
grep -n "if:" erpnext/.github/workflows/server-tests-postgres.yml
gh issue view 24389 --repo frappe/erpnext
```

Si la rama estable ya trae PostgreSQL con pruebas en cada PR y el módulo de calidad ha crecido
(flujos, control documental, auditorías), la decisión merece repensarse.
