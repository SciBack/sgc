---
title: Manual del módulo de Riesgos
description: Identificar, evaluar y tratar los riesgos de cada proceso, verificar que los controles funcionan, y reportar y evaluar los eventos que ya ocurrieron.
sidebar:
  order: 1
---

Este manual es para quien gestiona riesgos: los dueños de proceso, que identifican y tratan los
de su proceso, y la dirección de calidad, que verifica y decide. Incluye también lo que **cualquier
persona** de la institución puede hacer: reportar algo que ya pasó. Sigue la norma ISO 31000: se
identifica el riesgo, se evalúa, se trata, se vigila y se cierra.

:::tip[La regla de oro]
Un **riesgo** es algo que *puede* pasar; un **evento** es algo que *ya pasó*. Los riesgos los
gestionan los dueños de proceso. Los eventos los puede reportar cualquiera, y es la mejor manera de
que la institución se entere a tiempo.
:::

## 1. El área de Riesgos

Menú izquierdo → **Riesgos**. Tiene estas entradas:

![Portada del área de Riesgos](captura:riesgos-portada)

| Entrada | Qué es |
|---|---|
| **Portada del área** | Riesgos, tratamientos, eventos por evaluar, riesgos altos tras tratamiento y tratamientos vencidos |
| **Riesgos** | El registro de riesgos de la institución |
| **Eventos de riesgo** | Lo que ya ocurrió y alguien reportó |
| **Matrices de riesgo** | Las escalas de probabilidad e impacto y sus umbrales |
| **Evaluaciones de riesgo** | Cada medición de probabilidad e impacto de un riesgo |
| **Tratamientos de riesgo** | Los controles para reducir cada riesgo |
| **Matriz de riesgos (informe)** | Cada riesgo con su nivel antes y después del tratamiento |

## 2. Reportar un evento (cualquier persona)

Si ocurrió algo que puede afectar a la institución (una caída de un servicio, una pérdida de datos,
un plazo incumplido), repórtelo:

![Formulario para reportar un evento de riesgo](captura:riesgos-evento-nuevo)

1. Pulse **Reportar evento de riesgo**, en Inicio o en la portada del área.
2. Escriba **qué pasó** y **cuándo** (no puede ser una fecha futura), **qué ocurrió** con
   detalle, las **consecuencias** que vio y las **acciones inmediatas** que tomó. Si tiene una
   prueba, adjúntela como evidencia.
3. **Guardar.** El sistema registra quién lo reportó y cuándo.

Cada persona ve **solo lo que reportó**. Un evento puede describir a personas, así que solo lo leen
la dirección de calidad, los dueños de proceso, los auditores y el rectorado.

### Qué pasa después

| Estado | Quién actúa | Botón | Resultado |
|---|---|---|---|
| Reportado | Dirección de calidad | *Evaluar* | Pasa a evaluación |
| En evaluación | Dirección de calidad | *Confirmar* | Se abre la **no conformidad** (mayor o menor, a elegir), donde se analizan las causas y se planifica la corrección |
| En evaluación | Dirección de calidad | *Descartar* | Se cierra. **Exige escribir el motivo**, que le llega a quien lo reportó |

- **Quien reportó no decide sobre su reporte**, aunque sea de la dirección de calidad.
- **Lo decidido no se reescribe:** tras confirmar o descartar, el relato queda como se evaluó.
- El sistema sella quién decidió y cuándo.

## 3. Registrar un riesgo

**Riesgos → + Agregar**, o **Nuevo riesgo** en la portada. Lo hacen el dueño de proceso o la
dirección de calidad. Complete el **título**, la **descripción**, la **categoría** (estratégico,
operacional, de cumplimiento, financiero o reputacional), el **proceso** y la unidad, la **causa**,
la **consecuencia**, el **propietario** del riesgo y la **matriz** con que se evalúa.

## 4. El ciclo de un riesgo

| Estado | Quién actúa | Botón | Qué exige |
|---|---|---|---|
| Identificado | Dueño de proceso | *Evaluar* | Al menos una **evaluación** registrada |
| Evaluado | Dueño de proceso | *Iniciar tratamiento* | Al menos un **tratamiento** registrado |
| En tratamiento | Dueño de proceso | *Monitorear* | — |
| Monitoreado | Dirección de calidad | *Cerrar* | Todos sus tratamientos **verificados** |
| Monitoreado | Dirección de calidad | *Materializar* | — |
| Materializado | Dirección de calidad | *Cerrar* | Su no conformidad **cerrada** |

**Quien es propietario del riesgo no confirma su cierre ni su materialización:** lo hace otra
persona de la dirección de calidad.

### Cuando el riesgo se materializa

Pulsar **Materializar** crea sola la **no conformidad** del riesgo. A partir de ahí se trata en el
[módulo de Mejora continua](../mejora-continua/). El riesgo no se puede cerrar mientras esa no
conformidad siga abierta.

Un evento confirmado y un riesgo materializado no son lo mismo: el evento es una ocurrencia
concreta; materializar dice que el riesgo entero se cumplió. Eso lo decide la dirección de calidad.

## 5. Evaluar el riesgo

Desde el riesgo, en sus conexiones, añada una **evaluación de riesgo**:

- el **momento**: *inherente* (antes de los controles) o *residual* (después);
- la **probabilidad** y el **impacto**, según la escala de la matriz del riesgo.

El sistema calcula el **puntaje** y el **nivel** (bajo, moderado, alto o extremo) y registra quién
evaluó. Sin probabilidad e impacto no deja guardar.

Evalúe de nuevo, como *residual*, después de aplicar los controles: así se ve si bajó el nivel.

## 6. Tratar el riesgo

Desde el riesgo, añada un **tratamiento de riesgo**:

| Estado | Quién actúa | Botón | Qué exige |
|---|---|---|---|
| Planificado | Dueño de proceso | *Iniciar* | La **estrategia**, la descripción del control, un **responsable** y la **fecha de compromiso** |
| En ejecución | Dueño de proceso | *Marcar implementado* | La **evidencia** de que el control está implementado |
| Implementado | Dirección de calidad | *Verificar* o *Verificar no eficaz* | — |

- **Estrategias:** evitar, reducir, transferir o aceptar.
- **Quien implementó el tratamiento no lo verifica.** *Verificar no eficaz* lo devuelve a
  ejecución.
- Al verificarlo se registra el **resultado** y el **nivel residual**.
- Un riesgo cerrado o materializado no admite tratamientos nuevos.

## 7. Las matrices de riesgo

Cada matriz define los **niveles de probabilidad**, los **niveles de impacto** y los **umbrales**
que separan bajo, moderado, alto y extremo. Las mantiene la dirección de calidad; los riesgos se
evalúan con la que tengan asignada.

## 8. El informe Matriz de riesgos

Pone en una fila, para cada riesgo, su nivel **inherente** y su nivel **residual**, el **efecto del
tratamiento** (cuánto bajó), la estrategia y el propietario. Responde a la pregunta que no se ve
abriendo riesgo por riesgo: **si el tratamiento sirvió de algo**. Fíjese en dos señales:

- **Un riesgo alto o extremo sin estrategia:** es un riesgo aceptado sin decirlo.
- **Un residual igual o mayor que el inherente:** el tratamiento no funcionó, y hay que plantear
  otro, no repetir el mismo.

Es la foto que se lleva a la revisión por la dirección.

## Quién puede qué

| Acción | Dirección de calidad | Dueño de proceso | Cualquier persona |
|---|---|---|---|
| Reportar un evento | Sí | Sí | Sí |
| Evaluar, confirmar o descartar un evento | Sí, si no lo reportó | — | — |
| Registrar un riesgo, evaluarlo y tratarlo | Sí | Sí | — |
| Avanzar el riesgo hasta monitoreado | — | Sí | — |
| Iniciar e implementar un tratamiento | — | Sí | — |
| Verificar un tratamiento | Sí, si no lo implementó | — | — |
| Cerrar o materializar un riesgo | Sí, si no es su propietario | — | — |
| Mantener las matrices | Sí | — | — |
