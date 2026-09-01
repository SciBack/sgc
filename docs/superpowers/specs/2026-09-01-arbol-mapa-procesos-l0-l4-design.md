# Árbol nativo del mapa de procesos UPeU (N0-N4)

**Fecha:** 2026-09-01  
**Sistema:** SGC canónico sobre Frappe v16.32.0  
**Instancia alfa:** `https://calidad.upeu.edu.pe`

## Objetivo

Al abrir `Proceso` en Desk, mostrar de forma predeterminada una jerarquía navegable que
permita comprender los niveles superiores e inferiores del mapa institucional:

```text
N0 Macroproceso
└── N1 Proceso
    └── N2 Subproceso (solo cuando existe)
        └── N3 Procedimiento
            └── N4 Tarea / Actividad BPMN
```

La vista debe usar exclusivamente registros y archivos existentes. No crea procesos,
procedimientos ni tareas a partir de ejemplos o supuestos.

## Fuente institucional y corrección urgente

El PDF UPeU `Mapa-de-Procesos-UPeU-v8.0-2026.pdf`, código `E02-01-MP`, versión 8.0,
titula su sección 3 **Mapa de procesos de nivel 0** y su sección 4 **Descripción de los
macroprocesos**. Allí identifica 22 macroprocesos:

- estratégicos: `E01`-`E04`;
- clave/misionales: `C01`-`C13`;
- soporte: `S01`-`S05`.

Los 22 registros ya existen en producción con códigos y denominaciones oficiales. La
corrección consiste en marcarlos como nodos agrupadores (`is_group = 1`), sin cambiar sus
códigos ni crear descendientes. Así `nivel_bpm`, que es derivado, queda en `Macroproceso`.
Esta corrección pertenece a la capa UPeU porque el Mapa v8 es documentación del cliente.

## Alternativas evaluadas

### A. Árbol nativo compuesto en `Proceso` (seleccionada)

Usar el Tree View de Frappe y personalizar `proceso_tree.js` con un método de consulta que
proyecte nodos heterogéneos. Conserva el patrón de Desk, no introduce una SPA y permite que
`/desk/proceso` sea el punto de acceso único.

### B. Página Frappe independiente

Crear una Page `Mapa de Procesos`. Aísla mejor la visualización, pero duplica navegación y no
resuelve la expectativa de que la pantalla `Proceso` sea jerárquica.

### C. Convertir procedimientos y tareas en registros `Proceso`

Se descarta: duplicaría entidades, confundiría el modelo BPM y convertiría las cajas del BPMN
en datos operativos paralelos que podrían quedar desactualizados.

## Modelo y fuente de cada nivel

| Nivel | Fuente | Identificador de nodo | Acción |
| --- | --- | --- | --- |
| N0-N2 | DocType `Proceso` (`parent_proceso`) | `proceso:<name>` | Abrir `Proceso` |
| N3 | DocType `Procedimiento` (`proceso`) | `procedimiento:<name>` | Abrir `Procedimiento` |
| N4 | elementos Task del BPMN adjunto | `tarea:<procedimiento>:<bpmn-id>` | Abrir el procedimiento/BPMN origen |

Una tarea no se persiste como nuevo documento. Se lee del BPMN real asociado al procedimiento,
por lo que el árbol nunca se convierte en una segunda fuente de verdad.

## Backend

Se añadirá un módulo acotado de jerarquía con:

1. un método `@frappe.whitelist()` compatible con `get_tree_nodes`;
2. nodos raíz: procesos sin `parent_proceso`;
3. expansión de proceso: procesos hijos y procedimientos enlazados directamente;
4. expansión de procedimiento: tareas nombradas encontradas en el XML BPMN;
5. tareas como hojas.

El parser reconoce los tipos BPMN de tarea (`task`, `userTask`, `serviceTask`, `manualTask`,
`scriptTask`, `sendTask`, `receiveTask`, `businessRuleTask`) por nombre local XML. Excluye
eventos, gateways, carriles y flujos. Conserva el orden documental del BPMN y usa el `id` real
como respaldo cuando una caja no tiene nombre.

Las consultas respetan permisos de lectura de `Proceso` y `Procedimiento`. Los archivos privados
se resuelven mediante el DocType `File`; no se exponen rutas físicas ni contenido XML al cliente.
Un adjunto ausente o XML inválido deja al procedimiento sin tareas expandibles y registra el
problema para diagnóstico, sin fabricar nodos.

## Interfaz nativa

`Proceso` configurará `default_view = "Tree"` y `force_re_route_to_default_view = 1`.
La vista conservará expandir/contraer y refrescar de Frappe, pero deshabilitará crear, renombrar
y borrar desde el árbol compuesto para impedir operaciones sobre nodos virtuales.

Cada fila mostrará código, denominación y una etiqueta breve `N0`-`N4`. Los colores se limitan
a las etiquetas; no se añaden animaciones porque expandir el árbol es una interacción frecuente
y debe sentirse inmediata. La barra contextual ofrecerá solo acciones válidas:

- abrir proceso;
- abrir procedimiento;
- abrir el procedimiento que contiene una tarea.

La lista seguirá disponible desde el menú de vistas para trabajo tabular.

## Comportamiento con niveles opcionales

No se crean niveles huecos. Si un macroproceso no tiene procesos hijos, se muestra como nodo N0
sin expansión. Si un procedimiento cuelga directamente de un proceso N1 porque no existe un
subproceso N2 oficial, aparece directamente debajo. La profundidad visual representa relaciones
reales, no obliga a completar cinco escalones.

## Pruebas

1. RED/GREEN del parser BPMN: incluye tipos de tarea, ignora gateways/eventos y conserva datos
   reales (`id`, `name`).
2. RED/GREEN del proveedor de nodos: raíz, hijos de proceso, procedimientos y tareas.
3. Permisos: un usuario sin lectura no obtiene datos.
4. Metadatos: `Proceso` abre en Tree por defecto y no pierde su NestedSet.
5. Regresión: pruebas completas de la app SGC.
6. Producción: comprobar que existen 22 N0 oficiales y que S04 expande a sus procesos,
   subprocesos, cinco procedimientos DTI y tareas extraídas de sus BPMN privados.
7. Revisión visual en escritorio: jerarquía legible, etiquetas correctas, acciones coherentes y
   ausencia de datos inventados.

## Despliegue y reversión

El flujo será código local, commit, push, `git pull` en EC2, nueva imagen inmutable, migración y
verificación. Antes de recrear/reiniciar contenedores de producción se pedirá aprobación.

La corrección de los 22 macroprocesos es idempotente. La reversión de interfaz consiste en volver
a la imagen anterior; no se eliminan registros. Los procesos N1/N2 de DTI mantienen sus relaciones
actuales bajo `S04`.

## Criterios de aceptación

- `/desk/proceso` abre el Tree View.
- Aparecen exactamente los 22 macroprocesos N0 del Mapa v8.
- `S04` expande usando las relaciones reales ya registradas.
- Los procedimientos reales aparecen bajo su proceso/subproceso real.
- Las tareas N4 proceden de los BPMN adjuntos reales.
- La vista no permite editar nodos virtuales como si fueran `Proceso`.
- No se crea ningún dato operativo ficticio.
