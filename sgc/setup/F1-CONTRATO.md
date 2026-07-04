# F1 · Contrato de construcción del esqueleto (para los agentes)

> **Objetivo F1:** declarar los ~50 DocTypes del esqueleto (todas las ramas) en la app Frappe `sgc`. **Solo ESTRUCTURA** (campos, links, child tables, naming, permiso básico). **NADA de lógica** (workflows, server scripts, cálculos, is_submittable) — eso es F2+.
>
> **Cada agente escribe UN script Python** en `apps/sgc/sgc/setup/f1_<grupo>.py` con una función `run()` que crea sus DocTypes vía la API de Frappe (idempotente). El orquestador los ejecuta en orden de dependencia y valida. **Frappe valida el metadata al insertar** — por eso usamos su API, no JSON a mano.
>
> Detalle de CAMPOS por entidad: leer los insumos en `~/proyectos/upeu/calidad-upeu/doc/specs/sgc-frappe/insumos/` — **B** (meta-modelo base), **E** (dominio completo/ramas nuevas), **F** (procesos), **G** (correcciones de escalamiento). Este contrato fija **nombres, módulos y el patrón**; los insumos fijan los campos.

---

## 1. Reglas de oro (no negociables)

1. **Nombres de DocType = Title Case ASCII en español, sin acentos** (el `name` es identificador → sin tildes ni ñ). Ej: `No Conformidad`, `Valoracion Estandar`, `Programa Sede`, `Periodo Academico`, `Revision Direccion`. Los `label` de campos SÍ llevan acentos.
2. **Usar EXACTAMENTE los nombres del registro maestro (§3).** Todo `Link`/`Table` apunta a un nombre de esa lista. Si te falta un target, está en otro agente — úsalo por su nombre del registro, existirá al integrar.
3. **fieldname = snake_case.** Para los Links a los hubs, usa estos fieldnames canónicos (para consistencia entre ramas): `unidad_organica`, `programa`, `programa_sede`, `periodo_academico`, `marco_normativo`, `elemento_marco`, `indicador`, `evidencia`, `proceso`, `no_conformidad`, `documento_controlado`, `usuario` (→ target `User`).
4. **F1 = sin `is_submittable`, sin Workflow.** El `estado` es un campo `Select`. Los flujos vienen en F2.
5. **Idempotente:** usa el helper `_dt` (§2) que salta si el DocType ya existe.
6. **Ancla de scoping = `Programa Sede`, NO `Programa`** (corrección G). Toda entidad transaccional que se aísle por programa (Autoevaluacion, Evidencia, Hallazgo, No Conformidad, Auditoria, Comite, Objetivo Calidad, Informe Cumplimiento…) lleva `programa_sede` (Link → `Programa Sede`). `programa` (Link → `Programa`) solo para referir el plan canónico.
7. **No Conformidad = origen polimórfico** (corrección E §11): campos `origen_doctype` (Link → `DocType`) + `origen_id` (Dynamic Link, options=`origen_doctype`) + `origen_tipo` (Select legible).
8. **Indicador polimórfico** (corrección F): un solo `Indicador` con `categoria` (Select, incluye `Proceso`) + Link opcional `proceso`. NO crear `Indicador Proceso`.

---

## 2. Patrón de script (copiar el helper verbatim)

```python
"""F1 <grupo> — crea los DocTypes de <ramas>. Ejecutar:
bench --site sgc.localhost execute sgc.setup.f1_<grupo>.run
"""
import frappe

MODULE = "SGC Estructura"   # <-- el módulo de TU grupo (§3)

def _dt(name, fields, istable=0, is_tree=0, autoname=None, title_field=None,
        search_fields=None, track_changes=1):
    if frappe.db.exists("DocType", name):
        return
    doc = {
        "doctype": "DocType", "name": name, "module": MODULE, "custom": 0,
        "istable": istable, "is_tree": is_tree,
        "editable_grid": 1 if istable else 0,
        "track_changes": 0 if istable else track_changes,
        "fields": fields,
        "permissions": [] if istable else [
            {"role": "System Manager", "read": 1, "write": 1, "create": 1, "delete": 1}
        ],
    }
    if autoname: doc["autoname"] = autoname
    if title_field: doc["title_field"] = title_field
    if search_fields: doc["search_fields"] = search_fields
    frappe.get_doc(doc).insert(ignore_permissions=True)

def run():
    # ... tus _dt(...) en orden: primero child tables, luego los padres que las usan ...
    frappe.db.commit()
    print("f1_<grupo> OK")
```

### Semántica de campos (dict por campo)
- Claves: `fieldname` (snake), `fieldtype`, `label` (español con acentos), y opcionales `options`, `reqd`, `unique`, `in_list_view`, `in_standard_filter`, `default`, `read_only`, `permlevel`, `depends_on`, `description`.
- **Link**: `"fieldtype":"Link","options":"<Nombre DocType destino>"`.
- **Dynamic Link**: `"fieldtype":"Dynamic Link","options":"<fieldname del Link hermano que guarda el nombre del DocType>"`.
- **Table / Table MultiSelect**: `"options":"<Nombre Child DocType>"` (el child con `istable=1`).
- **Select**: `"options":"Uno\nDos\nTres"` (valores separados por `\n`).
- Fieldtypes válidos: `Data, Int, Float, Currency, Percent, Check, Date, Datetime, Time, Select, Small Text, Text, Long Text, Text Editor, Code, Link, Dynamic Link, Table, Table MultiSelect, Attach, Attach Image, JSON, Section Break, Column Break`.
- **Naming:** `autoname="field:codigo"` (usa el campo `codigo`, que debe ser `reqd:1, unique:1`) · o `autoname="format:NC-{YYYY}-{#####}"` · o `autoname="hash"`. Child tables: sin autoname.

### Ejemplo A — **Tree DocType** (`Unidad Organica`)
```python
_dt("Unidad Organica", [
    {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
    {"fieldname":"nombre","fieldtype":"Data","label":"Nombre","reqd":1,"in_list_view":1},
    {"fieldname":"tipo","fieldtype":"Select","label":"Tipo",
     "options":"Universidad\nSede\nVicerrectorado\nFacultad\nEscuela\nDireccion\nOficina\nUnidad","in_list_view":1},
    {"fieldname":"is_group","fieldtype":"Check","label":"Es grupo"},
    {"fieldname":"parent_unidad_organica","fieldtype":"Link","label":"Unidad padre","options":"Unidad Organica"},
], is_tree=1, autoname="field:codigo", title_field="nombre")
```
> Tree = `is_tree=1` + campo `is_group` (Check) + Link a sí mismo llamado `parent_<snake_del_doctype>`. Frappe gestiona `lft/rgt` solo. **Sede es un registro de `Unidad Organica` con `tipo=Sede`** (no un DocType aparte).

### Ejemplo B — **Dynamic Link** (`No Conformidad`, origen polimórfico)
```python
_dt("No Conformidad", [
    {"fieldname":"origen_doctype","fieldtype":"Link","label":"Tipo de documento origen","options":"DocType"},
    {"fieldname":"origen_id","fieldtype":"Dynamic Link","label":"Documento origen","options":"origen_doctype"},
    {"fieldname":"origen_tipo","fieldtype":"Select","label":"Origen",
     "options":"Autoevaluacion\nAuditoria\nQueja/Reclamo\nIndicador fuera de meta\nRevision por direccion\nRiesgo materializado\nIncumplimiento a ente\nProceso\nOtra","in_standard_filter":1},
    {"fieldname":"programa_sede","fieldtype":"Link","label":"Programa-Sede","options":"Programa Sede"},
    # ... resto de campos según insumo E §2.1 ...
], autoname="format:NC-{YYYY}-{#####}", title_field="titulo")
```

### Ejemplo C — **Child table + padre**
```python
# 1) el child PRIMERO (istable=1, sin permissions ni autoname)
_dt("Nivel Escala", [
    {"fieldname":"codigo","fieldtype":"Data","label":"Código","in_list_view":1,"reqd":1},
    {"fieldname":"etiqueta","fieldtype":"Data","label":"Etiqueta","in_list_view":1},
    {"fieldname":"orden","fieldtype":"Int","label":"Orden","in_list_view":1},
], istable=1)
# 2) el padre lo referencia por Table
_dt("Escala Valoracion", [
    {"fieldname":"codigo","fieldtype":"Data","label":"Código","reqd":1,"unique":1,"in_list_view":1},
    {"fieldname":"nombre","fieldtype":"Data","label":"Nombre","reqd":1},
    {"fieldname":"niveles","fieldtype":"Table","label":"Niveles","options":"Nivel Escala"},
], autoname="field:codigo", title_field="nombre")
```

---

## 3. Registro maestro de DocTypes (autoridad de nombres) + módulo por agente

**Orden de ejecución (lo hace el orquestador):** A1 → A2 → B1 → B2 → B3 → B4.
Kind: `Doc` (normal) · `Tree` · `Child` (istable=1).

### Agente A1 — módulo `SGC Estructura` (config/estructura; sin dependencias)
`Marco Normativo` (Doc) · `Nivel Marco` (Child) · `Elemento Marco` (Tree) · `Escala Valoracion` (Doc) · `Nivel Escala` (Child) · `Indicador` (Doc) · `Ficha Indicador` (Doc) · `Indicador Criterio` (Child) · `Unidad Organica` (Tree) · `Programa` (Doc) · `Programa Sede` (Doc) · `Periodo Academico` (Doc).
> `Elemento Marco` es Tree (estándar→criterio recursivo), `parent_elemento_marco`. `Indicador` incluye `categoria` (Select con `Proceso`) y Link opcional `proceso` (→ `Proceso`, existe en B4; el Link se declara igual). `Programa Sede`: `programa` (Link Programa) + `sede` (Link Unidad Organica) + `escuela` (Link Unidad Organica) + `licencia` + `estado`.

### Agente A2 — módulo `SGC Nucleo` (acreditación + mejora core; depende de A1)
`Autoevaluacion` (Doc) · `Valoracion Criterio` (Doc) · `Valoracion Estandar` (Doc) · `Evidencia` (Doc) · `Trazabilidad` (Doc) · `Valor Indicador` (Doc) · `Documento Controlado` (Doc) · `No Conformidad` (Doc) · `Hallazgo` (Doc) · `Plan Mejora` (Doc) · `Accion Mejora` (Doc).
> `Autoevaluacion` ancla en `programa_sede` + `marco_normativo` + `periodo_academico`. `Valoracion Estandar.nivel` con `permlevel:1`. `Trazabilidad` tiene `evidencia` + `elemento_marco` + `proceso` (los 3). No Conformidad = ejemplo B. CAPA: `Accion Mejora` con `hallazgo` (Link) y `no_conformidad` (Link).

### Agente B1 — módulo `SGC Auditoria` (auditoría + revisión dirección; depende A1/A2)
`Programa Auditoria` (Doc) · `Auditoria` (Doc) · `Criterio Auditoria` (Child) · `Equipo Auditoria` (Child) · `Hallazgo Auditoria` (Doc) · `Informe Auditoria` (Doc) · `Revision Direccion` (Doc) · `Entrada Revision` (Child) · `Salida Revision` (Child). → insumo E ramas 1 y 4.

### Agente B2 — módulo `SGC Riesgos` (riesgos/GRC + obligaciones; depende A1/A2)
`Matriz Riesgo` (Doc) · `Riesgo` (Doc) · `Evaluacion Riesgo` (Doc) · `Tratamiento Riesgo` (Doc) · `Ente Externo` (Doc) · `Obligacion Ente` (Doc) · `Entrega Obligacion` (Doc). → insumo E ramas 3 y 5.

### Agente B3 — módulo `SGC Gobierno` (satisfacción + comités/política; depende A1/A2)
`Grupo Interes` (Doc) · `Instrumento` (Doc) · `Aplicacion Instrumento` (Doc) · `Resultado Instrumento` (Doc) · `Comite` (Doc) · `Miembro Comite` (Child) · `Reunion` (Doc) · `Acuerdo` (Doc) · `Politica Calidad` (Doc) · `Objetivo Calidad` (Doc). → insumo E ramas 6 y 7.

### Agente B4 — módulo `SGC Procesos` (procesos + IAC; depende A1/A2 y de B2 para IAC→Riesgo/Obligacion)
`Proceso` (Tree) · `Ficha Caracterizacion Proceso` (Doc) · `Entrada Proceso` (Child) · `Salida Proceso` (Child) · `Actividad Proceso` (Child) · `Riesgo Proceso` (Child) · `Registro Proceso` (Child) · `Doc Proceso Link` (Child) · `Indicador Proceso Link` (Child) · `Cambio Ficha` (Child) · `Procedimiento` (Doc) · `Interaccion Proceso` (Doc) · `Informe Cumplimiento` (Doc) · `Cumplimiento CBC` (Child). → insumos F (procesos) y E rama 8 (IAC).

---

## 4. Entrega de cada agente
- UN archivo `apps/sgc/sgc/setup/f1_<grupo>.py` (grupo = `estructura|nucleo|auditoria|riesgos|gobierno|procesos`) con `run()`.
- Dentro de `run()`: child tables primero, luego padres. Cierra con `frappe.db.commit()`.
- Devuelve al orquestador: lista de DocTypes creados, campos con `permlevel`, y cualquier Link a un target de OTRO agente (para verificar el orden).
- **NO ejecutes** el script (no tienes el site); solo escríbelo. El orquestador ejecuta y valida.
