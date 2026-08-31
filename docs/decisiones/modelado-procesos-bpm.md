# Modelado de procesos: la jerarquía BPM y cómo no romperla

Convención adoptada el **2026-08-31**, tras cometer y corregir los errores que se listan
abajo al modelar el primer proceso de nivel 1 del sistema. Aplica a **todo** el trabajo de
caracterización de procesos del SGC, para cualquier cliente. La instanciación de la
codificación por cliente vive en su capa institución (para UPeU:
`instituciones/upeu/calidad-upeu/docs/codificacion-procesos-upeu.md`).

## La jerarquía (cinco niveles)

| Nivel | Elemento | Qué es | Regla |
|---|---|---|---|
| N0 | **Macroproceso** | El conjunto global. | Es grupo; agrupa procesos. |
| N1 | **Proceso** | Etapas que transforman entradas en salidas de valor. | Se **caracteriza** (ficha SIPOC). |
| N2 | **Subproceso** | División de un proceso que agrupa **varios** procedimientos con un fin y un responsable. | Opcional — ver regla del nivel hueco. |
| N3 | **Procedimiento** | La secuencia paso a paso: *cómo / quién / cuándo*. | Se documenta y se **diagrama en BPMN**. |
| N4 | **Tarea / Actividad** | La acción atómica; no se divide más. | Son las **cajas del BPMN**. |

## Reglas duras

1. **Identifica el nivel antes de nombrar nada.** Proceso ≠ Subproceso ≠ Procedimiento. El
   error más común es llamar «subproceso» a un proceso, o «actividad del proceso» a lo que en
   realidad es una tarea de un procedimiento.
2. **No se inventan códigos ni denominaciones.** Salen del **mapa de procesos oficial del
   cliente**. Si el mapa define el nivel 1, se usa su código y su nombre tal cual.
3. **La ficha de caracterización es de un PROCESO (N1)** y en su descomposición lista sus
   **procedimientos** (o subprocesos), **nunca una lista suelta de tareas**. Después del
   proceso vienen sus procedimientos, no sus tareas.
4. **El BPMN modela un PROCEDIMIENTO (N3)** —o un subproceso—, no «el proceso». Sus cajas son
   **tareas (N4)**. Un mismo flujo no se lista dos veces (como «actividades» del proceso y como
   «pasos» del procedimiento): es una sola cosa, en su nivel.
5. **No crees un nivel hueco.** Un **subproceso (N2) con un único procedimiento hijo** sobra —
   ensucia la jerarquía tanto como saltarse un nivel. El N2 se introduce solo cuando agrupa
   **varios** procedimientos. Y nunca se salta un nivel que sí existe.
6. **Los códigos de procedimiento siguen la convención del cliente** (área-tipo-correlativo),
   no un formato inventado sobre la marcha.

## Blindaje: tres pilares (un proceso no se defiende con criterio propio)

Todo proceso/procedimiento modelado se sostiene —y se defiende ante el dueño del proceso y
ante un acreditador— en tres fuentes verificables e independientes:

1. **Estructura → el mapa de procesos oficial del cliente.** Da el código, el nombre y el nivel.
2. **Buenas prácticas → un marco de gestión reconocido** (ITIL v4, COBIT 2019, ISO/IEC 20000-1,
   ISO 9001…). Da el «cómo debería ser». Se nombran las prácticas concretas que instancia el flujo.
3. **Evidencia → el sistema operativo real** (la herramienta ITSM, el CMDB, los registros). Da el
   «cómo es de verdad». El flujo refleja la práctica observada, no un supuesto.

Si falta alguno de los tres, el modelado es una opinión, no una caracterización.

## Tres planos que NO se mapean 1:1

El error de fondo más frecuente es confundir tres cosas distintas. Mantenerlas separadas
evita casi todos los desajustes:

| Plano | Responde a | Qué es |
|---|---|---|
| **Organigrama** | el **QUIÉN** | áreas y personas (la estructura organizacional) |
| **Mapa de procesos** (oficial del cliente) | el **QUÉ** | los procesos |
| **Marco de referencia** (ITIL v4, COBIT…) | el **CÓMO** | buenas prácticas |

No tienen por qué coincidir como espejo: **un proceso lo pueden ejecutar varias áreas**, y el
marco es una **guía**, no la nomenclatura obligatoria del mapa. Cada plano entra por su sitio:
el **organigrama** son los **carriles/roles** del BPMN (quién hace cada tarea) y el
**responsable** del proceso; el **mapa** da el **código y el nombre**; el **marco** se cita en el
**pilar 2 del blindaje** (las prácticas que instancia el flujo).

## Cuando el mapa no encaja con el marco: dos vías, nunca la unilateral

Cuando el mapa oficial no encaja del todo con el marco de referencia —p.ej. una práctica central
del marco (Service Desk en ITIL) no tiene proceso propio, o un proceso del mapa es más una
actividad que una práctica— hay **dos vías legítimas, y ninguna es cambiar el mapa por cuenta
propia**:

1. **Desplegar el rigor del marco en los niveles inferiores (N2–N4).** Los subprocesos y
   procedimientos sí se nombran según las prácticas del marco; el mapa de nivel 1 queda intacto.
   Sirve cuando la brecha se puede absorber por debajo.
2. **Solicitud formal de cambio al mapa.** Si la brecha está en el propio **nivel 1** (un proceso
   mal nombrado, o uno que falta), el **dueño del proceso** puede **solicitar el cambio** al área
   que gobierna el mapa, con una **propuesta técnica justificada** (diagnóstico contra el marco,
   evidencia operativa, impacto). El dueño **propone**; la autoridad de procesos **decide**.

Nunca se edita el mapa unilateralmente. La observación de una brecha no es el fin del camino: si
el dueño la respalda, escala a solicitud de cambio por la vía 2.

## Cómo lo materializa Frappe

- **`Proceso`** es un árbol (NestedSet): N0/N1/N2 son nodos con `parent_proceso` e `is_group`.
- **`Ficha Caracterizacion Proceso`** caracteriza un `Proceso`; su tabla de actividades enlaza a
  **`Procedimiento`**.
- **`Procedimiento`** lleva el BPMN en `diagrama_flujo`; sus tareas viven en ese diagrama / su
  documento controlado.

## Checklist antes de dar por bueno un proceso modelado

- [ ] ¿El código y el nombre salen del mapa oficial del cliente (no inventados)?
- [ ] ¿Está claro de qué **nivel** es cada documento (proceso vs procedimiento)?
- [ ] ¿La ficha lista **procedimientos**, no tareas sueltas?
- [ ] ¿El BPMN es de un **procedimiento** y sus cajas son tareas?
- [ ] ¿No hay ningún nivel hueco (subproceso con un solo hijo) ni salto de nivel?
- [ ] ¿El código de procedimiento sigue la convención del cliente?
- [ ] ¿Están los **tres pilares** (mapa oficial + marco de gestión + evidencia operativa)?

## Por qué existe esta convención

Al modelar el primer proceso de nivel 1 del SGC se cometieron, y se corrigieron, estos fallos:
se codificó un proceso con un número que el mapa oficial ya tenía asignado a otro; se llamó
«subproceso» a un proceso; se listaron «7 actividades» del proceso que en realidad eran las
tareas de un procedimiento; y se inventó un código de procedimiento que no seguía la convención
institucional. Ninguno lo detecta una revisión superficial: por eso la convención es explícita y
trae checklist.

Relacionado: [`bpmn-herramientas.md`](bpmn-herramientas.md) (con qué se genera/edita el BPMN).
