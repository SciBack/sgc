# Diagramas BPMN del SGC

Un `.bpmn` por cada workflow del sistema. **Se generan; no se escriben a mano**:
`sgc/bpmn.py` los deriva de los specs de `sgc/setup/f*_workflow*.py`. El código
es la fuente de verdad y el diagrama es la vista.

```bash
python3 -c "import sys; sys.path.insert(0,'.'); from sgc.bpmn import exportar_todos; exportar_todos('docs/diagramas/bpmn')"
```

Ya no hace falta un bench para regenerarlos: si los módulos de `setup/` no se
pueden importar (fuera del servidor no hay `frappe`), los specs se leen del
código con `ast`. Antes fallaba en silencio y devolvía cero diagramas — por eso
fue tan fácil olvidarse de regenerar cuando nació el workflow del hallazgo de
auditoría.

**El layout SÍ se respeta.** Si recolocas las cajas en Camunda, la siguiente
regeneración conserva tus posiciones y solo actualiza la semántica. Lo que no
sobrevive es mover *flechas*: esas salen del código.

## El orden de los ficheros es el recorrido del sistema

El número no es decorativo ni alfabético: sigue las **dependencias reales**, de
modo que quien los recorra en orden encuentre hecho lo que cada uno necesita.

| # | Proceso | Por qué va aquí |
|---|---|---|
| 01 | Documento Controlado | La base normativa. Sin documentos aprobados no hay nada que evidenciar. |
| 02 | Evidencia | El insumo transversal; enlaza al documento controlado del paso 01. |
| 03 | Autoevaluación | El núcleo de acreditación: consume la evidencia del 02. |
| 04 | Aplicación de Instrumento | Las encuestas publican los indicadores que usa la autoevaluación. |
| 05 | Informe de Cumplimiento | El otro entregable regulatorio (CBC/SUNEDU). |
| 06 | Programa de Auditoría | El plan anual que gobierna las auditorías. |
| 07 | Auditoría | Se ejecuta dentro de ese programa. |
| 08 | Hallazgo de Auditoría | Lo que produce la auditoría; puede escalar a no conformidad. |
| 09 | Hallazgo | Donde desemboca lo detectado en cualquiera de los anteriores. |
| 10 | No Conformidad | El hallazgo confirmado. |
| 11 | Plan de Mejora | La respuesta a la no conformidad. |
| 12 | Acción de Mejora | Las acciones concretas del plan. |
| 13 | Riesgo | Gestión preventiva, en paralelo al ciclo correctivo. |
| 14 | Tratamiento de Riesgo | Lo que se hace con cada riesgo. |
| 15 | Revisión por la Dirección | Cierra el ciclo (ISO 9001 §9.3): consume las salidas de todo lo demás. |

Un workflow nuevo que nadie ordene sale como `99-…`: aparece el último y el
prefijo repetido canta que falta colocarlo.

## De qué norma nace cada proceso

Desde el 2026-08-23 cada diagrama lleva dentro, en el `<bpmn:documentation>` de
su proceso, la norma que lo respalda. No es un comentario del fichero: es el
elemento que BPMN 2.0 reserva para esto, va lo primero dentro de `bpmn:process`
—el esquema de la OMG lo exige ahí— y cualquier modelador lo muestra al
seleccionar el proceso. Así el diagrama viaja con su base normativa en vez de
depender de que quien lo abra ya la conozca.

El texto sale de `DOCUMENTACION_NORMATIVA` en `sgc/bpmn.py`, un mapa explícito
`DocType → texto`. **La regla de admisión es estrecha a propósito:** solo entra
lo contrastado contra fuente primaria (la norma en `sciback/biblioteca/`) o ya
citado en el código del propio proceso.

| # | Proceso | Norma que lo respalda |
|---|---|---|
| 01 | Documento Controlado | ISO 21001 cl. 7.5 y 7.5.3.2.g (ciclo de vida y segregación de funciones) |
| 02 | Evidencia | Modelos de acreditación del Coneau: 52 evidencias en programas (Tabla 8), 84 en institucional |
| 03 | Autoevaluación | Modelos del Coneau (10/53/29 y 9/68/37) · escala NL/L/LP · Tabla 9 (vigencia) · Tabla 10 (excelencia: 16 y 20 puntos) |
| 04 | Aplicación de Instrumento | **Sin documentación** — ver abajo |
| 05 | Informe de Cumplimiento | 8 condiciones básicas del Modelo de Licenciamiento Institucional, RCD 006-2015-SUNEDU/CD (+ RS 054-2017) · Ley Universitaria art. 13.4 y 13.5, en la redacción de la Ley 32105 |
| 06 | Programa de Auditoría | ISO 9001:2015 §9.2 · ISO 19011 cl. 5 · ISO 21001 |
| 07 | Auditoría | ISO 9001:2015 §9.2 · ISO 19011 · ISO 21001 cl. 9.2.2 e) |
| 08 | Hallazgo de Auditoría | ISO 19011 · ISO 9001:2015 §10.2 (escalamiento) |
| 09 | Hallazgo | ISO 9001:2015 §10 y §10.2 |
| 10 | No Conformidad | ISO 9001:2015 §10.2 |
| 11 | Plan de Mejora | ISO 9001:2015 §10.2 |
| 12 | Acción de Mejora | ISO 9001:2015 §10.2 (revisión de la eficacia) |
| 13 | Riesgo | ISO 9001:2015 §6.1 y §10.2 · ISO 31000 §6.4.2 |
| 14 | Tratamiento de Riesgo | ISO 31000 (tratamiento y riesgo residual) |
| 15 | Revisión por la Dirección | ISO 9001:2015 §9.3.1/§9.3.2/§9.3.3 y §5.1.1 · ISO 21001 §9.3 |

**El hueco del 04 es información, no un olvido.** Ninguna norma que el proyecto
tenga verificada exige aplicar encuestas: los indicadores del modelo del Coneau
sí están normados, pero que se midan por encuesta es decisión de la casa. Se deja
en blanco antes que escribir una cita que no se sostenga, porque una cita falsa
se cita.

Dos matices que el texto de los diagramas ya recoge y conviene no perder:

- **La licencia ya no se renueva.** El modelo de renovación (RCD 091-2021) quedó
  derogado por la Ley 32105; lo que se demuestra ahora es cumplimiento
  *continuo* (art. 13.4 de la Ley Universitaria, en la redacción que le dio esa
  ley), y el informe anual es una de las herramientas que el art. 13.5 enumera.
  Por eso el 05 es anual.
- **Licenciamiento y acreditación no se mezclan.** Las 8 condiciones básicas son
  el permiso para operar; los 10 o 9 estándares del Coneau son un sello
  voluntario. El Modelo de Acreditación Institucional del Coneau (2026) §4.2 dice
  que sus estándares se definieron revisando las condiciones de la Sunedu «para
  diferenciar los niveles de exigencia».

## Qué muestran y qué no

Ver [`CONCORDANCIA.md`](../CONCORDANCIA.md): estos diagramas representan
**estados, transiciones y quién puede ejecutarlas**, pero hoy no representan las
reglas que condicionan cada paso ni cómo un proceso dispara al siguiente.
Conviene saberlo antes de usarlos como referencia única.

## Cómo verlos

Son XML. Se abren con [Camunda Modeler](https://camunda.com/download/modeler/) o
arrastrándolos a [demo.bpmn.io](https://demo.bpmn.io). Aún **no hay visor dentro
del sistema** (estaba previsto en `docs/decisiones/bpmn-herramientas.md`, punto
2, y no se implementó).
