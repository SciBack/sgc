---
title: Manual del módulo de Mejora continua
description: Registrar hallazgos, salidas no conformes y no conformidades, analizar sus causas, y llevar los planes y acciones de mejora hasta verificar que funcionaron.
sidebar:
  order: 1
---

Este manual es para quien detecta, trata y verifica problemas: los responsables de calidad, los
dueños de proceso, los auditores y la dirección de calidad. Sigue el camino de un problema desde
que alguien lo ve hasta que se comprueba que la solución funcionó.

:::tip[La regla de oro]
Hay **una sola cadena** para cualquier problema, venga de donde venga: se detecta, se analiza su
causa, se planifica qué hacer, se hace y **se verifica que funcionó**. Nada se cierra porque
alguien diga que está hecho: se cierra con evidencia y lo cierra otra persona.
:::

## 1. El área de Mejora continua

**Cómo entrar:** arriba a la izquierda, pulse el nombre del área en la que está (el que lleva
la flecha ⌄) → **Módulos** → **Mejora continua**.

![Menú «Módulos» con Mejora continua resaltado](captura:navegacion-mejora-continua)

Se abre la portada del área, y el menú de la izquierda muestra sus entradas:

![Portada del área de Mejora continua](captura:mejora-portada)

| Entrada | Qué es |
|---|---|
| **Portada del área** | Lo abierto, lo vencido y lo que espera verificación, con sus cifras |
| **Hallazgos** | Lo que encontró una autoevaluación o una supervisión |
| **No conformidades** | Los incumplimientos del sistema de gestión, con su análisis de causa |
| **Salidas no conformes** | Un servicio o producto concreto que se entregó mal |
| **Planes de mejora** | El conjunto de acciones para resolver uno o varios problemas |
| **Acciones de mejora** | Cada tarea concreta del plan, con responsable y fecha |
| **Informe de mejoramiento continuo** | El estado de toda la cadena |
| **Informe de salidas no conformes** | Las salidas registradas y cómo se trataron |

## 2. Qué registrar en cada caso

| Si… | Registre… |
|---|---|
| una autoevaluación o una supervisión encontró una debilidad | un **Hallazgo** |
| una auditoría interna encontró algo | un hallazgo de auditoría (ver el [manual de Auditoría](../auditoria/)) |
| se entregó mal algo concreto: un acta, un certificado, una constancia | una **Salida no conforme** |
| el sistema de gestión falla en un requisito | una **No conformidad** |
| ocurrió algo que puede afectar a la institución | un evento de riesgo (ver el [manual de Riesgos](../riesgos/)) |

Todos esos caminos terminan, cuando hace falta, en una **No conformidad**, y desde ella en un
**Plan de mejora** con sus **Acciones**. La no conformidad guarda siempre de dónde vino.

## 3. Hallazgos

**Registrar:** **Hallazgos → + Agregar**, o **Hallazgo** en la portada. Indique el **tipo**
(fortaleza, debilidad u oportunidad de mejora), el **origen**, el **criterio** del marco al que
se refiere, la **autoevaluación** si viene de una, la **descripción** y la **severidad**. El código
se genera solo.

| Estado | Quién actúa | Botón |
|---|---|---|
| Abierto | Responsable de calidad | *Tratar* |
| En tratamiento | Responsable de calidad | *Enviar a verificacion* |
| Verificación | Dirección de calidad | *Cerrar eficaz*, *Cerrar no eficaz* o *Reabrir* |

**Escalar a no conformidad.** Si el hallazgo revela que el sistema falla, pulse **Escalar a no
conformidad**. Se crea la no conformidad con el criterio, la unidad y el programa del hallazgo, y
los dos quedan enlazados. El botón solo aparece en debilidades y oportunidades de mejora (una
fortaleza no es un problema) y a quien puede crear no conformidades.

## 4. Salidas no conformes

Una salida no conforme es **algo concreto que se entregó mal**: un acta con notas mal cargadas, un
certificado con un error, una constancia fuera de plazo. No es lo mismo que una no conformidad:
aquella dice que el sistema falló; esta, que una entrega salió mal. Un caso aislado se queda
aquí.

**Registrar:** **Salidas no conformes → + Agregar**. Obligatorios: título, origen (interno, reclamo
de usuario, auditoría o proveedor externo), proceso, descripción y requisito que se incumplió.
Puede registrarla casi cualquiera que trabaje en calidad o en un proceso.

| Estado | Quién actúa | Botón | Qué exige |
|---|---|---|---|
| Detectada | Dueño de proceso o dirección de calidad | *Iniciar tratamiento* | Un responsable del tratamiento |
| En tratamiento | Dueño de proceso o dirección de calidad | *Registrar tratamiento* | La decisión y las acciones tomadas |
| Tratada | Dirección de calidad | *Verificar* o *Devolver a tratamiento* | La evidencia del tratamiento y marcar *Resultado comprobado* |
| Verificada | Dirección de calidad | *Cerrar* | — |

**La decisión** es una de cuatro: corregir, autorizar bajo concesión, suspender la entrega o
retirar lo entregado.

**Una concesión** (aceptar algo que no cumple) exige justificar por qué se acepta, y **no la
puede autorizar quien detectó ni quien registró** la salida. **La verificación** tampoco la hace
quien la trató ni quien decidió. El sistema **sella** quién decidió y quién verificó: lo que se
escriba a mano en esos campos no cuenta.

**Escalar.** Si la salida no es un caso aislado (el mismo error se repite, el control no existía),
pulse **Escalar a no conformidad**, elija si es mayor o menor, y las dos quedan enlazadas.

## 5. No conformidades

**Registrar:** **No conformidades → + Agregar**, o se crean solas al escalar un hallazgo, una
salida no conforme, un hallazgo de auditoría o un riesgo que se materializa. Tipos: **no
conformidad mayor**, **menor**, **potencial no conformidad** (todavía no incumple, pero va a
incumplir si no se actúa), **observación** y **oportunidad de mejora**.

![Formulario de una no conformidad nueva](captura:mejora-nc-nueva)

| Estado | Quién actúa | Botón | Qué exige para pasar |
|---|---|---|---|
| Abierta | Responsable de calidad | *Analizar causa* | Un responsable |
| En análisis | Responsable de calidad | *Tratar* | El análisis de causa, si lo requiere |
| En tratamiento | Responsable de calidad | *Enviar a verificacion* | La fecha de compromiso, y un plan de mejora o una corrección inmediata |
| En verificación | Dirección de calidad | *Cerrar eficaz*, *Cerrar no eficaz* o *Reabrir tratamiento* | La evidencia de cierre |

### El análisis de causa

Una no conformidad **mayor** lo exige siempre; las demás, si se marca *Requiere análisis de
causa*. Para pasar a tratamiento hace falta:

1. La **metodología**: cinco porqués, espina de pescado (Ishikawa), Pareto, lluvia de ideas u
   otra.
2. Las **causas identificadas**: al menos una, y al menos una marcada como **causa raíz**.
3. En cada causa, **el dato que pide la metodología**: el nivel en la cadena de porqués, la
   categoría de la espina (personas, método, material, máquina, medición, entorno) o la frecuencia
   para Pareto.

La tabla de causas se ordena según la metodología elegida.

### El cierre

Se cierra con la **evidencia de cierre** adjunta, y **quien trató la no conformidad no puede
cerrarla**: lo hace otra persona de la dirección de calidad. *Cerrar no eficaz* deja constancia de
que la solución no funcionó; *Reabrir tratamiento* la devuelve para intentarlo de nuevo.

## 6. Planes de mejora

Un plan agrupa las acciones que resuelven uno o varios problemas.

1. **Crear:** **Planes de mejora → + Agregar**. Indique título, el documento de origen y el
   **responsable**.
2. **Enlazarlo a la no conformidad:** en la no conformidad, campo **Plan de mejora**.
3. **Añadir las acciones** con **Crear ▾ → Acción de mejora**, en el propio plan (ver la sección 7).
4. **Aprobar y ejecutar:** lo hace la dirección de calidad, y no puede aprobarlo quien lo creó.
   Exige responsable y al menos una acción. Al aprobarlo, el plan **se envía por correo** a su
   responsable y al de cada acción, con la tabla de qué, quién y para cuándo.
5. **Seguimiento:** el **avance**, el **semáforo** (verde, ámbar, rojo) y la **fecha de
   compromiso** del plan se calculan solos a partir de sus acciones.
6. **Cerrar plan:** solo cuando **todas sus acciones están verificadas como eficaces**. Si falta
   alguna, el sistema dice cuántas y cuáles.

## 7. Acciones de mejora

1. **Crear:** desde el plan, con **Crear ▾ → Acción de mejora** (o el **+** de *Acciones de mejora* en
   su pestaña **Resumen**). Indique la
   descripción, el **tipo** (correctiva, preventiva o de mejora), el **responsable** y la **fecha
   de compromiso**.
2. **Qué causa ataca:** si la acción nace de una no conformidad, pulse **Elegir causa** y escoja
   una de las causas de su análisis. Así se puede responder qué acción resuelve cada causa.
3. **Iniciar:** exige responsable y fecha de compromiso. El responsable recibe una **tarea** en sus
   pendientes.
4. **Marcar ejecutada** cuando esté hecha, y adjunte la **evidencia de cierre**.
5. **Verificar:** la dirección de calidad la marca **eficaz** (exige la evidencia) o **no eficaz**.
   Quien creó la acción no puede verificarla. Una acción no eficaz se **reabre**.

Una vez verificada como eficaz, la evidencia ya no se puede quitar.

## 8. Los informes

- **Informe de mejoramiento continuo:** el estado de la cadena completa, de los hallazgos a las
  acciones.
- **Informe de salidas no conformes:** las salidas registradas, su decisión y su verificación. En
  modo **Detalle** muestra también quién intervino en cada paso.

## Quién puede qué

| Acción | Dirección de calidad | Responsable de calidad | Dueño de proceso | Auditor interno |
|---|---|---|---|---|
| Registrar un hallazgo | Sí | Sí | — | Sí |
| Registrar una salida no conforme | Sí | Sí | Sí | Sí |
| Tratar una salida no conforme | Sí | — | Sí | — |
| Verificar y cerrar una salida no conforme | Sí | — | — | — |
| Registrar una no conformidad | Sí | Sí | — | Sí |
| Analizar y tratar una no conformidad | — | Sí | — | — |
| Cerrar una no conformidad | Sí, si no la trató | — | — | — |
| Crear un plan o una acción | — | Sí | Sí | — |
| Aprobar y cerrar un plan | Sí, si no lo creó | — | — | — |
| Iniciar y ejecutar una acción | — | Sí | — | — |
| Verificar una acción | Sí | — | — | — |
| Borrar | Nadie: se cierra como eficaz o no eficaz | | | |

El analista de la dirección de calidad puede registrar y editar como la dirección, pero no ejecuta
los cierres ni las verificaciones.
