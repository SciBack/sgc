# Concordancia entre los diagramas BPMN y el sistema real

**Fecha:** 2026-08-23 · **Versión en producción:** `sgc-frappe:v95`

Contrastación de los 15 `.bpmn` contra el comportamiento comprobado en
producción, recorriendo los 8 flujos punta a punta con usuarios reales por rol.

---

## Lo que concuerda

**Estados, transiciones y roles: los 15, sin excepción.** No es casualidad ni
mérito: los diagramas se *generan* de los mismos specs que crean los workflows
en Frappe, así que no pueden divergir por construcción. Un diagrama que
contradijera al motor sería un fallo del generador, no del proceso.

Lo que sí se comprobó ejecutando —y podría haber fallado— es que el motor
respeta lo dibujado:

- **Segregación de funciones real.** El rol equivocado recibe `Not a valid
  Workflow Action`; quien crea un documento no puede aprobarlo (`Self approval
  is not allowed`) en las transiciones marcadas de control.
- **Los carriles se cumplen.** Cada tarea está en el carril de su rol y solo ese
  rol la ejecuta: la Autoridad Aprobadora presenta a SUNEDU y la DPGC no; el
  Rectorado cierra la Revisión por la Dirección y la DPGC no puede, ni estando
  en «Realizada».
- **Las devoluciones existen y funcionan** (Observar, Devolver a planificada,
  Verificar no eficaz), incluidas las tres que se añadieron al detectar que un
  documento observado quedaba atascado.

---

## Lo que NO concuerda

### 1. «Vencida» existe en el sistema y no está en el diagrama 🔴

`Evidencia` tiene **cinco** estados en su Select y el diagrama solo dibuja
**cuatro**. Falta `Vencida`, y no es teórico: un job diario
(`sgc.tasks.marcar_evidencias_vencidas`) mueve evidencias a ese estado, lo cual
se verificó funcionando en producción.

Ocurre **fuera del motor de workflow** (`db.set_value` directo), así que no deja
rastro en el historial del documento ni transición que dibujar. Es el único
DocType de los 15 con esta discordancia — los otros 14 cuadran exactamente.

**Qué significa para quien lea el diagrama:** creerá que una evidencia validada
se queda validada para siempre.

**Cómo se arreglaría:** darle a `Vencida` un estado de workflow y una transición
temporizada (evento de temporizador BPMN), o al menos declararlo en el diagrama
como estado terminal alcanzado por el sistema.

### 2. 42 reglas gobiernan el flujo y ninguna aparece ⚠️

Los diagramas muestran *que* existe una flecha, no *cuándo* está disponible. Hay
**42 validaciones** en los controladores que bloquean transiciones dibujadas
como si fueran libres. Por proceso: Revisión por la Dirección 7, Auditoría 6,
Documento Controlado 6, No Conformidad 6, Aplicación de Instrumento 5, Informe
de Cumplimiento 4, Evidencia 3, Programa de Auditoría 2, Hallazgo de Auditoría
2, Riesgo 1.

Ejemplos comprobados en vivo, todos invisibles en el diagrama:

| Proceso | La flecha está dibujada… | …pero antes exige |
|---|---|---|
| Informe de Cumplimiento | Presentar a SUNEDU | ninguna CBC sin evaluar, y justificación en cada una que no cumpla |
| Revisión por la Dirección | Cerrar revisión | las 3 salidas §9.3.3 con responsable **y** el acta en PDF |
| Aplicación de Instrumento | Cerrar aplicación | fecha de fin de campo registrada |
| Auditoría | Iniciar ejecución | equipo auditor con al menos un miembro independiente |
| Hallazgo de Auditoría | Escalar a NC | que la no conformidad exista |

**Qué significa:** Calidad puede leer el diagrama, planificar un paso y
encontrarse con que el sistema no la deja. La regla es correcta; lo que falta es
que esté dicha.

**Cómo se arreglaría:** BPMN tiene con qué — condiciones en el flujo de salida
del gateway, o anotaciones de texto. El generador tendría que leerlas del
controlador, que hoy no hace.

### 3. Los 15 diagramas están aislados; el sistema los encadena ⚠️

Cada `.bpmn` es un proceso cerrado en su propio pool. Pero el sistema **salta de
un proceso a otro**, y esos saltos no se dibujan:

| Cuando… | el sistema… | y el diagrama |
|---|---|---|
| un riesgo se materializa | crea una **No Conformidad** | no lo muestra |
| se escala un hallazgo de auditoría | crea una **No Conformidad** | no lo muestra |
| se cierra una aplicación de instrumento | publica **Valor Indicador** | no lo muestra |
| se valida una evidencia | sincroniza **Trazabilidad** | no lo muestra |
| se cierra una autoevaluación | promueve la **vigencia oficial** | no lo muestra |

**Qué significa:** el orden `01…15` de los ficheros expresa una secuencia que
los diagramas, por sí solos, no cuentan. Quien vea uno aislado no sabrá de dónde
le llega el trabajo ni a dónde va.

**Cómo se arreglaría:** BPMN lo resuelve con *message flows* entre pools, o con
un diagrama de colaboración de nivel superior que enlace los 15.

---

## Riesgo de deriva

Nada compara automáticamente los `.bpmn` en disco contra lo que generaría el
código. **Ya falló una vez**: al crear el workflow del hallazgo de auditoría
hubo 15 workflows y 14 diagramas hasta que alguien lo notó.

Un test que regenere en memoria y falle si el disco difiere cerraría el hueco, y
ahora es viable: el generador ya no necesita un bench para leer los specs.

**Ojo con Camunda:** abrir un diagrama y guardarlo reescribe el fichero. El
layout se conserva al regenerar, pero **editar flechas a mano se pierde** — y
puede romper el modelo. Pasó el 2026-08-23: una edición manual en
`evidencia.bpmn` dejó el estado final «Válida» inalcanzable y una referencia a
un flujo borrado. El fichero seguía siendo XML válido; el proceso, no.
