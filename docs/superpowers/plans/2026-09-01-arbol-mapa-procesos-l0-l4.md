# Árbol nativo del mapa de procesos N0-N4 - Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Hacer que `Proceso` abra como árbol nativo y proyecte macroprocesos, procesos, subprocesos, procedimientos y tareas BPMN reales, registrando correctamente los 22 macroprocesos N0 del Mapa UPeU v8.

**Architecture:** `Proceso` conserva su NestedSet para N0-N2. Un proveedor Tree de solo lectura compone procedimientos y tareas extraídas del único `.bpmn` adjunto; los nodos virtuales nunca se persisten. La lista oficial UPeU permanece en `upeu-ops` y llama una operación canónica validada para clasificar raíces existentes.

**Tech Stack:** Frappe Framework 16.32.0, Python 3.14, PostgreSQL, Frappe Tree View, XML `ElementTree`, JavaScript Desk, Docker Compose.

---

## Estructura de archivos

- Modify: `sgc/sgc_procesos/doctype/proceso/proceso.py` - reglas de dominio y operación segura para clasificar un macroproceso raíz.
- Modify: `sgc/sgc_procesos/doctype/proceso/test_proceso.py` - pruebas de derivación y clasificación.
- Create: `sgc/sgc_procesos/doctype/proceso/proceso_tree.py` - parser BPMN y proveedor jerárquico.
- Create: `sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py` - pruebas parser/API/permisos.
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso_tree.js` - presentación y acciones seguras del Tree.
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso.json` - Tree como vista predeterminada sin forzar la salida de Lista.
- Create in UPeU repo: `services/sgc/frappe/data/mapa-v8-macroprocesos.sh` - allowlist institucional idempotente y verificación.
- Create in UPeU repo: `services/sgc/frappe/data/mapa-v8-macroprocesos.test.sh` - prueba estática de allowlist/seguridad.
- Create in UPeU repo: `services/sgc/frappe/data/verificar-arbol.py` - controles reproducibles de integridad y latencia.
- Create in UPeU repo: `services/sgc/frappe/data/verificar-arbol.test.sh` - contrato estático del verificador.

### Task 1: Operación canónica segura para clasificar macroprocesos

**Files:**
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso.py`
- Modify: `sgc/sgc_procesos/doctype/proceso/test_proceso.py`

- [ ] **Step 1: escribir pruebas fallidas**

Probar que `asegurar_macroproceso_raiz(name, denominacion, categoria)`:

```python
def test_clasifica_raiz_existente_sin_cambiar_estado(self):
    proceso = crear_proceso(codigo="TEST-MP", proceso="Macro oficial", nivel="Soporte")
    estado = proceso.estado
    resultado = asegurar_macroproceso_raiz("TEST-MP", "Macro oficial", "Soporte")
    proceso.reload()
    self.assertEqual((proceso.is_group, proceso.nivel_bpm), (1, "Macroproceso"))
    self.assertEqual(proceso.estado, estado)
    self.assertEqual(resultado["changed"], True)
```

Agregar casos: segunda ejecución `changed=False`; nombre/categoría distintos; padre no vacío;
registro inexistente. Los últimos cuatro no deben crear ni alterar datos. Probar también
`restaurar_clasificacion_raiz(name, denominacion, categoria, is_group)`: solo acepta una raíz
existente que coincide exactamente, restaura `is_group`, deriva `nivel_bpm` mediante `save()` y
preserva cualquier valor previo de `estado`.

- [ ] **Step 2: ejecutar RED**

Run in a Frappe test site:

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso
```

Expected: FAIL porque `asegurar_macroproceso_raiz` no existe.

- [ ] **Step 3: implementar lo mínimo**

Las dos funciones no serán whitelisted. Deben cargar el documento, exigir `parent_proceso` vacío
y coincidencia exacta de denominación/categoría, asignar únicamente `is_group`, ejecutar
`save(ignore_permissions=True)` y devolver `{name, changed, is_group, nivel_bpm}`. No cambian
`estado`, nombre, propietario ni relaciones. Corregir el comentario que hoy llama Procesos a los
22 nodos raíz UPeU; mantener la regla canónica genérica raíz-grupo/raíz-hoja.

- [ ] **Step 4: ejecutar GREEN y regresión focalizada**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso
```

Expected: módulo PASS, salida sin warnings nuevos.

- [ ] **Step 5: commit**

```bash
git add sgc/sgc_procesos/doctype/proceso/proceso.py sgc/sgc_procesos/doctype/proceso/test_proceso.py
git commit -m "feat(procesos): clasificar macroprocesos raíz con validación"
```

### Task 2: Seed UPeU de los 22 macroprocesos oficiales

**Files (repo `/Users/alberto/proyectos/upeu/upeu-ops`):**
- Create: `services/sgc/frappe/data/mapa-v8-macroprocesos.sh`
- Create: `services/sgc/frappe/data/mapa-v8-macroprocesos.test.sh`

- [ ] **Step 1: escribir prueba fallida del script**

La prueba debe extraer la allowlist y exigir los 22 códigos/denominaciones/categorías exactos;
invocación exclusiva a `asegurar_macroproceso_raiz` en modo `apply` y a
`restaurar_clasificacion_raiz` en modo `rollback`; ausencia de `insert`, `delete`, `rename`, SQL
y de cualquier asignación/mutación de `estado` (`doc.estado`, `db_set`, `set_value`). Se permite
leer `estado` en snapshot/verificación para demostrar que se preserva.

Allowlist literal (fuente: Mapa de Procesos UPeU v8.0, páginas 7-8):

```text
E01|Gobierno institucional y gestión estratégica|Estratégico
E02|Aseguramiento y gestión de la calidad|Estratégico
E03|Gestión del modelo educativo universitario adventista|Estratégico
E04|Gestión de marketing y comunicación|Estratégico
C01|Admisión|Clave
C02|Matrícula|Clave
C03|Enseñanza y aprendizaje|Clave
C04|Generación del conocimiento e innovación|Clave
C05|Vinculación con la sociedad|Clave
C06|Desarrollo espiritual|Clave
C07|Aseguramiento del perfil de egreso|Clave
C08|Graduación y titulación|Clave
C09|Gestión de egresados|Clave
C10|Gestión docente|Clave
C11|Gestión del servicio al estudiante|Clave
C12|Gestión de operaciones académicas|Clave
C13|Gestión de enseñanza y aprendizaje digital|Clave
S01|Gestión administrativa y financiera|Soporte
S02|Gestión del talento humano|Soporte
S03|Gestión de infraestructura física|Soporte
S04|Gestión tecnológica|Soporte
S05|Gestión de bienes y servicios|Soporte
```

- [ ] **Step 2: ejecutar RED**

```bash
sh services/sgc/frappe/data/mapa-v8-macroprocesos.test.sh
```

Expected: FAIL porque el script aún no existe.

- [ ] **Step 3: implementar script idempotente**

El script tendrá `snapshot`, `apply`, `verify <archivo-snapshot>`,
`compare <archivo-snapshot>` y `rollback <archivo-snapshot>`; no aceptará otro modo. No
seleccionará snapshots por glob ni por
“último archivo”: `verify` y `rollback` requieren la ruta explícita devuelta por `snapshot`.
`snapshot` corre antes de la primera mutación y escribe fuera del repo
`/opt/sgc/releases/data/mapa-v8-<UTC>-pre.json` con permisos 600. Por cada código guarda
`name`, denominación, categoría, `parent_proceso`, `is_group`, `nivel_bpm` y `estado`.

Cada línea de la allowlist será `codigo|denominacion|categoria`. En `apply`, por cada una ejecutar
dentro de `backend`:

```bash
bench --site calidad.upeu.edu.pe execute \
  sgc.sgc_procesos.doctype.proceso.proceso.asegurar_macroproceso_raiz \
  --args '["E01","Gobierno institucional y gestión estratégica","Estratégico"]'
```

El script usa `set -eu`, resuelve el contenedor desde el compose productivo y aborta ante cualquier
precondición. `verify <snapshot>` exige exactamente los 22 registros raíz con `is_group=1` y
`nivel_bpm=Macroproceso`, pero no exige ni modifica un estado particular: compara cada `estado`
contra el snapshot explícito. `compare <snapshot>` exige igualdad exacta de `is_group`,
`nivel_bpm` y `estado` respecto de la foto. `rollback` valida que el JSON corresponda a los 22 códigos y restaura solo
`is_group` mediante `restaurar_clasificacion_raiz`; `nivel_bpm` se deriva en `save()`. No crea,
renombra, borra ni reinicia contenedores.

- [ ] **Step 4: escribir RED del verificador productivo**

`verificar-arbol.test.sh` exige que `verificar-arbol.py` importe el endpoint canónico, compruebe
los 22 códigos, invariantes NestedSet, siete descendientes reales bajo S04 (`S04.01`-`S04.07`), cinco códigos de
procedimientos DTI y tres umbrales separados: raíz/expansión ordinaria p95 `<500 ms` y primera
lectura BPMN `<1 s`. Debe fallar si falta cualquiera de estos contratos.

```bash
sh services/sgc/frappe/data/verificar-arbol.test.sh
```

Expected: FAIL porque `verificar-arbol.py` aún no existe.

- [ ] **Step 5: implementar `verificar-arbol.py` y pasar GREEN**

El script es de solo lectura y se ejecuta dentro de un único `bench console` para conservar las
mediciones. Llama `get_children` con usuario Administrator, recorre recursivamente todos los
tokens devueltos igual que `Expand All`, compara las cinco tareas con el contenido de sus BPMN y
mide con `time.perf_counter`: 30 llamadas calientes de raíz (descartar 5), 30 expansiones de un
nodo Proceso con hijos (descartar 5) y una primera lectura sin cache de cada BPMN. Calcula p95 con
`statistics.quantiles(..., method="inclusive")`; aborta si raíz/expansión ≥500 ms o BPMN ≥1 s.

```bash
sh services/sgc/frappe/data/verificar-arbol.test.sh
```

- [ ] **Step 6: GREEN, commit y push del repo UPeU**

```bash
sh services/sgc/frappe/data/mapa-v8-macroprocesos.test.sh
sh services/sgc/frappe/data/verificar-arbol.test.sh
git add services/sgc/frappe/data/mapa-v8-macroprocesos.sh services/sgc/frappe/data/mapa-v8-macroprocesos.test.sh services/sgc/frappe/data/verificar-arbol.py services/sgc/frappe/data/verificar-arbol.test.sh
git commit -m "feat(sgc): clasificar los 22 macroprocesos del Mapa v8"
git push origin main
```

### Task 3: Parser seguro de tareas BPMN

**Files:**
- Create: `sgc/sgc_procesos/doctype/proceso/proceso_tree.py`
- Create: `sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py`

- [ ] **Step 1: pruebas RED del parser puro**

Probar `extraer_tareas_bpmn(content)` con namespaces prefijado/default y los ocho tipos Task;
ignorar gateway/event/lane/sequenceFlow; conservar orden; usar ID si falta nombre; rechazar DTD,
ENTITY, más de 5 MiB, XML inválido, ID vacío y duplicado.

- [ ] **Step 2: ejecutar RED**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
```

Expected: FAIL por módulo/función ausente.

- [ ] **Step 3: implementación mínima segura**

Usar `xml.etree.ElementTree.fromstring`; comprobar tamaño antes de parsear y rechazar
`<!DOCTYPE`/`<!ENTITY` sin distinción de mayúsculas. Devolver dicts `{id, name, task_type}`.
Definir excepción de dominio `BpmnInvalido`.

- [ ] **Step 4: ejecutar GREEN y commit**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
```

```bash
git add sgc/sgc_procesos/doctype/proceso/proceso_tree.py sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py
git commit -m "feat(procesos): extraer tareas reales de BPMN con seguridad"
```

### Task 4: Proveedor Tree N0-N4 con permisos

**Files:**
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso_tree.py`
- Modify: `sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py`

- [ ] **Step 1: pruebas RED del contrato Frappe**

Crear fixtures con nombres únicos en `setUp` y eliminarlos en `tearDown`: tres `Proceso`
(raíz/grupo, proceso, subproceso), un `Procedimiento`, un `File` privado `.bpmn` adjunto de forma
exacta, un usuario con lectura de ambos DocTypes y otro usuario con lectura de `Proceso` pero sin
lectura de `Procedimiento`. Crear el File con `content=xml`,
`attached_to_doctype="Procedimiento"` y `attached_to_name=<name>`.

Probar raíz dos veces (`parent` omitido y `parent=""`) y exigir resultado idéntico; nodos
`{value,title,expandable,node_type,doctype,docname,file_name,bpmn_id}`,
IDs tipados, proceso→hijo/procedimiento, procedimiento→tareas, padre forjado, Guest, falta de
lectura, `File` ajeno, PDF y BPMN inválido. Verificar que `expandable` solo revela hijos visibles.
Para el usuario con lectura exclusiva de `Proceso`, exigir que el nodo Proceso no anuncie ni
devuelva Procedimiento/tareas. Simular `Expand All` recorriendo recursivamente desde ambas formas
de raíz y llamando el endpoint con cada `value` expandible; debe terminar sin tokens rechazados,
duplicados ni ciclos y producir el mismo conjunto de nodos.

- [ ] **Step 2: ejecutar RED**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
```

Expected: FAIL porque `get_children` no existe.

- [ ] **Step 3: implementar endpoint**

`@frappe.whitelist()` `get_children(doctype, parent="", is_root=False, **filters)` exige
`doctype == "Proceso"`, usuario no Guest y lectura. Usar `frappe.get_list` + `has_permission` por
documento. Tokens permitidos: `proceso:`, `procedimiento:` y `tarea:`; tarea es hoja. Resolver
`File` por URL + attachment exacto, comprobar tamaño y leer con `get_content()`. Log de parser
agregado por `File.name:modified` mediante cache. No usar rutas físicas ni `get_all`.

- [ ] **Step 4: GREEN, rendimiento focal y commit**

Validar que la raíz use consultas agrupadas para no hacer N+1 sobre los 22 macroprocesos.

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
git add sgc/sgc_procesos/doctype/proceso/proceso_tree.py sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py
git commit -m "feat(procesos): componer árbol N0-N4 con permisos"
```

### Task 5: Tree View predeterminado y acciones seguras

**Files:**
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso.json`
- Modify: `sgc/sgc_procesos/doctype/proceso/proceso_tree.js`
- Modify: `sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py`

- [ ] **Step 1: pruebas RED de configuración**

Comprobar metadatos `default_view == "Tree"`, `force_re_route_to_default_view == 0`; JS contiene
el endpoint propio, `disable_add_node: true`, toolbar reemplazado, no acciones Add/Rename/Delete,
navegación por `node.data.doctype/docname` y `frappe.utils.escape_html` para todo título dinámico.

- [ ] **Step 2: ejecutar RED**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
```

Expected: FAIL porque JSON/JS conservan configuración actual.

- [ ] **Step 3: implementar JS nativo**

Configurar `frappe.treeview_settings["Proceso"]`. `get_label` deriva N0-N4 de `node_type`, usa
badges nativos discretos y escapa título/ID. No añadir animaciones. Toolbar único `Abrir` para
Proceso/Procedimiento/tarea; raíz sin acción. La lista permanece disponible.

- [ ] **Step 4: GREEN y commit**

```bash
bench --site test_site.localhost run-tests --app sgc --module sgc.sgc_procesos.doctype.proceso.test_proceso_tree
git add sgc/sgc_procesos/doctype/proceso/proceso.json sgc/sgc_procesos/doctype/proceso/proceso_tree.js sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py
git commit -m "feat(procesos): abrir el mapa en árbol nativo"
```

### Task 6: Verificación integral, publicación y producción

**Files:**
- Update: `docs/superpowers/plans/2026-09-01-arbol-mapa-procesos-l0-l4.md` (marcar pasos)

- [ ] **Step 1: verificación local completa**

```bash
ruff check sgc/sgc_procesos/doctype/proceso/proceso.py sgc/sgc_procesos/doctype/proceso/test_proceso.py sgc/sgc_procesos/doctype/proceso/proceso_tree.py sgc/sgc_procesos/doctype/proceso/test_proceso_tree.py
python3 -m compileall -q sgc
git diff --check main...HEAD
```

Ejecutar en test site todas las pruebas de `sgc`; esperado 0 fallos. El `ruff check sgc` global
queda fuera de este cambio porque el baseline confirmado tiene 63 hallazgos preexistentes; no se
introducen hallazgos en archivos tocados.

- [ ] **Step 2: revisión final independiente**

Revisar cumplimiento de la spec, seguridad, permisos, XSS, XML y ausencia de datos inventados.

- [ ] **Step 3: push y preparación de imagen**

Push de la rama; integrar a main según reglas del repo; en EC2 hacer `git pull --ff-only` de
canónico y `upeu-ops`; construir imagen candidata con `backend-release.sh build-and-prepare` y
validar `config`. Esto todavía no reinicia producción.

- [ ] **Step 4: solicitar aprobación de reinicio**

No ejecutar `deploy`, `docker compose up`, recreación o reinicio sin autorización explícita.

- [ ] **Step 5: migrar, aplicar seed y verificar producción**

Tras aprobación: desplegar candidato, `bench migrate`, `clear-cache`; ejecutar `snapshot`, guardar
la ruta exacta emitida, luego `apply`, `verify <ruta-snapshot>`, volver a ejecutar `apply` y exigir
22 resultados `changed=false`; repetir `verify <ruta-snapshot>`.
El script `verificar-arbol.py`, ejecutado en un único `bench console`, debe comprobar:

- exactamente 22 raíces N0 oficiales y ninguna con `parent_proceso`;
- invariantes NestedSet `lft < rgt`, rangos no duplicados y cada hijo contenido en su padre;
- S04 conserva sus siete procesos/subprocesos reales ya registrados (`S04.01`-`S04.07`);
- aparecen los cinco procedimientos DTI reales y cada tarea N4 coincide con el XML BPMN;
- 30 llamadas calientes a la raíz y 30 expansiones ordinarias, descartando las primeras 5 de
  cada grupo, con p95 menor de 500 ms; primera lectura de cada BPMN menor de 1 s.

La validación visual se hace en navegador sobre `/desk/proceso`: capturar el árbol expandiendo
S04 hasta una tarea, cambiar mediante el selector nativo a `Vista de Lista`, comprobar que siguen
visibles los registros y volver a `Árbol`. No se crea ningún documento durante esta prueba.

- [ ] **Step 6: promover o revertir**

Promover solo con verificaciones verdes. Si falla, ejecutar rollback de imagen y luego
`mapa-v8-macroprocesos.sh rollback /opt/sgc/releases/data/mapa-v8-<UTC>-pre.json`; repetir
un nuevo modo read-only `compare <snapshot>` del script para demostrar que `is_group`,
`nivel_bpm` y `estado` regresaron a sus valores previos, sin borrar registros. Por tanto, los
modos definitivos son `snapshot`, `apply`, `verify <snapshot>`, `compare <snapshot>` y
`rollback <snapshot>`.
