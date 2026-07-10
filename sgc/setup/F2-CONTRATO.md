# F2 · Contrato — profundizar la autoevaluación (rama de agosto)

> **Objetivo F2:** que la autoevaluación de Enfermería contra **CONEAU Programas 2025** funcione end-to-end sobre el esqueleto F1: cargar el marco desde YAML, valorar criterios, **agregar a nivel de estándar NL/L/LP** (el sistema PROPONE, el humano CONFIRMA), proponer vigencia, y disparar el flujo CAPA (hallazgo→no conformidad→plan). Evidencias con filestore local (MinIO es swap de backend en despliegue).
>
> Base: los 66 DocTypes F1 ya existen (ver `F1-CONTRATO.md`). La lógica va en los **controladores** `sgc/sgc/<modulo>/doctype/<name>/<name>.py` y en módulos nuevos `sgc/sgc/scoring.py` / `sgc/sgc/capa.py`. YAML fuente: el modelo de acreditación vigente del cliente (p. ej. CONEAU Programas 2025), extraído de la normativa oficial.
>
> **Los 3 agentes NO ejecutan** (no tienen el site). El orquestador ejecuta, integra y hace el E2E.

---

## 1. Campos a AÑADIR a DocTypes F1 (autoridad — todos los agentes usan estos nombres)

Los añade **un solo script** `f2_fields.py` (lo escribe el agente S). Patrón: cargar el DocType, `doc.append("fields", {...})`, `doc.save()` con `frappe.flags.in_patch=True`.

| DocType | Campo nuevo | Tipo | Notas |
|---|---|---|---|
| `Valoracion Criterio` | `cumple` | Select | `Cumple\nCumple con debilidad\nNo cumple` (juicio de campo) |
| `Valoracion Criterio` | `debilidad` | Text | descripción de la debilidad/OM si aplica |
| `Valoracion Criterio` | `comentario` | Text | sustento del juicio |
| `Valoracion Estandar` | `nivel_propuesto` | Select | `NL\nL\nLP` **read_only** (lo calcula el motor) |
| `Valoracion Estandar` | `confirmado` | Check | el humano confirmó el `nivel` oficial (permlevel 1) |
| `Autoevaluacion` | `vigencia_propuesta` | Select | `En proceso\nAcreditado 3 anios\nAcreditado 6 anios\nAcreditado 8 anios` read_only |
| `Autoevaluacion` | `avance_pct` | Percent | % de criterios valorados (read_only) |

> `Valoracion Estandar.nivel` (permlevel 1, F1) sigue siendo el **oficial confirmado por humano**. El motor nunca lo escribe; escribe `nivel_propuesto`.

---

## 2. Algoritmo de scoring NL/L/LP (Sección IX del Modelo — literal)

**Regla por estándar** (agente S → `sgc/sgc/scoring.py`):
```
proponer_nivel_estandar(autoevaluacion, estandar):   # estandar = Elemento Marco depth=2
  criterios = hijos assessable (depth=3) del estandar en el marco
  vals = [Valoracion Criterio(autoevaluacion, ci) for ci in criterios]
  si algún ci sin valorar        -> nivel_propuesto = None (incompleto)
  elif algún val.cumple=="No cumple"            -> "NL"   # no cumple todos los criterios
  elif algún val.cumple=="Cumple con debilidad" -> "L"    # cumple todos, con debilidades
  else (todos "Cumple")                          -> "LP"   # PROPUESTO; requiere que el humano
                                                            # revise evolución de indicadores (±3%, 4 semestres)
```
> **LP NO es mecánico** (norma IX): el motor propone LP, pero la confirmación exige revisar la evolución de los indicadores asociados. El humano fija `nivel` (permlevel 1) y marca `confirmado`. El motor SOLO escribe `nivel_propuesto`.

**Regla de vigencia** (Tabla 9, sobre los `nivel` CONFIRMADOS de los 10 estándares):
```
proponer_vigencia(autoevaluacion):
  niveles = [ve.nivel for ve in valoraciones_estandar confirmadas]
  si no están los 10 confirmados     -> None (incompleto)
  elif algún == "NL"                 -> "En proceso"
  elif todos == "LP"                 -> "Acreditado 6 anios"   # (8 años requiere ≥16 pts excelencia, Tabla 10 → F6)
  else (todos L, o combo L/LP)       -> "Acreditado 3 anios"
```
Disparo: recomputar el estándar cuando cambia una `Valoracion Criterio` (hook `on_update`); recomputar `avance_pct` y `vigencia_propuesta` en un método de `Autoevaluacion` (botón "Recalcular").

---

## 3. Mapeo del YAML CONEAU → DocTypes (agente L → `f2_load_coneau.py`)

Formato intuitem library. Idempotente (buscar por `codigo`/`ref_id` antes de crear).
- `objects.framework.scores_definition` → **`Escala Valoracion`** `CONEAU-NLLP` + 3 **`Nivel Escala`** (NL=0/L=1/LP=2, con `etiqueta` y `descripcion`).
- `objects.framework` → **`Marco Normativo`** `codigo=CONEAU-Programas-2025`, `nombre`, `descripcion`, `ente=SINEACE`, `escala_valoracion=CONEAU-NLLP`.
- `requirement_nodes` → **`Elemento Marco`** (Tree). Mapear `urn`→clave, `parent_urn`→`parent_elemento_marco`, `ref_id`, `name`→`nombre`, `description`, `annotation`→`nota_normativa`/anotación, `assessable`, `depth`→`nivel`/`tipo` (depth1=raíz, depth2=`Estandar`, depth3=`Criterio`), `marco_normativo`. `is_group=1` para no-hojas.
- `objects.reference_controls` (ID1..ID29) → **`Indicador`** (`codigo=ID#`, `nombre`, `categoria`=de `category`) + **`Ficha Indicador`** (parsear del `description`: objetivo, valor_referencial/umbral, interpretación, fuente_dato, variables, formula). `dominio_dato` según el tipo de fuente (satisfacción→D4, estadístico→D2, etc.; si dudoso, dejar en blanco).
- `reference_controls` bajo cada nodo estándar → **`Indicador Criterio`** (link Indicador↔Elemento Marco del estándar).

Verificación esperada tras cargar: 1 Marco, 1 Escala+3 niveles, **64 Elemento Marco** (1 raíz+10 estándares+53 criterios), **29 Indicador**+fichas, N Indicador Criterio.

---

## 4. Workflow + CAPA (agente W → `f2_workflow.py` + `sgc/sgc/capa.py`)

**Workflows** (DocType `Workflow` vía API; estados con `Role`):
- `Autoevaluacion`: `Borrador → En evaluacion → En revision → Cerrada`. Campo de estado = `estado`. Transiciones con rol `Responsable de Programa`/`DPGC`.
- `No Conformidad`: `Abierta → En analisis → En tratamiento → En verificacion → Cerrada eficaz | Cerrada no eficaz`.
> Usar el DocType `Workflow` nativo (workflow_state_field=`estado`, states con doc_status 0, transitions). NO reimplementar.

**Flujo CAPA** (`sgc/sgc/capa.py`), funciones:
- `generar_hallazgo(valoracion_criterio)`: si `cumple in (No cumple, Cumple con debilidad)` → crea `Hallazgo` (`tipo`=Debilidad, `origen`=autoevaluación, link a `elemento_marco` criterio, `programa_sede`, `proceso` si aplica).
- `escalar_a_no_conformidad(hallazgo)`: crea `No Conformidad` (`origen_doctype=Autoevaluacion`, `origen_id`, `origen_tipo=Autoevaluacion`), setea `hallazgo.no_conformidad` + `escalado_a_nc=1`.
- `crear_plan(no_conformidad)`: crea `Plan Mejora` (origen polimórfico) + permite `Accion Mejora`.
> Reutiliza el CAPA de F1 (Hallazgo/Plan Mejora/Accion Mejora). No dupliques.

---

## 5. Entrega de cada agente
- **L** → `apps/sgc/sgc/setup/f2_load_coneau.py` con `run()`.
- **S** → `apps/sgc/sgc/setup/f2_fields.py` (`run()`, añade los campos §1) + `apps/sgc/sgc/scoring.py` (funciones §2) + hook `on_update` en el controlador `sgc/sgc/sgc_nucleo/doctype/valoracion_criterio/valoracion_criterio.py` que llame al motor.
- **W** → `apps/sgc/sgc/setup/f2_workflow.py` (`run()`, crea los Workflow) + `apps/sgc/sgc/capa.py` (funciones §4).
- Idempotente. Español. Devuelve: qué creó/añadió, y qué asume `[VERIFICAR]`.
