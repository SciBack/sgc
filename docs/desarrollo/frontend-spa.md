# Frontend: la SPA

`frontend/` es una SPA Vue 3 + [frappe-ui](https://github.com/frappe/frappe-ui) +
Vite + Tailwind, servida bajo `/sgc/*`. Es **genérica sobre el meta de cada DocType**:
no hay un formulario hardcodeado por tipo de documento.

## Estructura

```
frontend/src/
├── pages/
│   ├── Home.vue                  Landing/dashboard de la SPA
│   ├── Tablero.vue                Tablero de indicadores/avance
│   ├── DoctypeList.vue             Listado genérico de cualquier DocType
│   ├── DocForm.vue                 Formulario genérico de cualquier DocType
│   └── AutoevaluacionDetalle.vue   Pantalla específica de valoración de criterios
├── components/
│   ├── autoevaluacion/
│   │   └── CriterioRow.vue         Fila de valoración de un criterio + evidencias vinculadas
│   └── form/
│       ├── AttachField.vue         Render del fieldtype Attach (subida de archivo)
│       ├── ChildTableField.vue     Editor de tablas hijas (child tables)
│       └── DocConnections.vue      Bloque de "Document Links" — vincula/lista registros relacionados
├── composables/
│   ├── useDoctypeMeta.js           Lee el meta de un DocType (campos, tablas hijas, links)
│   └── useLinkSearch.js            Autocomplete de campos Link
├── stores/                         Estado global (Pinia)
├── layouts/                        Layout base de la SPA
└── router.js                       Rutas cliente (vue-router)
```

## Cómo funciona el formulario genérico (`DocForm.vue`)

1. `useDoctypeMeta` obtiene la definición del DocType (campos, tipos, tablas hijas,
   `links` — el bloque de Document Links del meta).
2. Separa `formFields` (los que se pueblan/guardan) de `visibleFields` (los que se
   renderizan): los campos read-only **vacíos** se ocultan del formulario — reduce
   ruido visual para el usuario final sin perder los que sí tienen valor.
3. Respeta `depends_on`: un campo con esa condición solo se muestra si se cumple
   (evita, por ejemplo, mostrar "Archivo" y "Enlace (URL)" simultáneamente cuando el
   `Tipo` determina cuál aplica).
4. **Guardado**: usa `frappe.client.save` (el doc completo) cuando el DocType tiene
   tablas hijas — `set_value` no persiste child tables — y conserva `set_value` para
   documentos sin tablas hijas (evita una regresión de rendimiento innecesaria).
5. Attach: `AttachField.vue` sube el archivo vía `FileUploader` de frappe-ui; al
   guardar, el `file_url` resultante se persiste como cualquier otro campo.
6. Conexiones: `DocConnections.vue` lee el bloque `links` del meta para listar y
   crear inline registros de otros DocTypes que apuntan a este documento — es el
   mecanismo genérico detrás de, por ejemplo, vincular una Evidencia a un criterio
   vía Trazabilidad (ver [Evidencias y trazabilidad](../manual-uso/evidencias-trazabilidad.md)).

## Componente específico: `CriterioRow.vue`

Es la única pieza de UI no genérica: la fila de un criterio dentro de la pantalla de
autoevaluación. Permite editar el juicio (`cumple`/`estado`/`observacion`) y, al
expandir el detalle, carga perezosamente (`evidencias_de_elemento`, consulta inversa
sobre Trazabilidad) las evidencias que ya lo respaldan.

## Qué NO cubre todavía la SPA

Algunas pantallas siguen cayendo al **Desk** nativo de Frappe (no reimplementadas en
la SPA): informes con estructuras de tabla hija muy específicas, y cualquier
formulario que dependa de vistas de reporte de Frappe (list views con filtros
avanzados, por ejemplo). El Desk siempre está disponible como fallback — la SPA no
reemplaza a Frappe, lo complementa para los flujos de uso más frecuentes del comité.
