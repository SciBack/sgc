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
