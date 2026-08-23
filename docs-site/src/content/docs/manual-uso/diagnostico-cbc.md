---
title: Diagnóstico de Condiciones Básicas de Calidad (CBC)
description: Cómo se evalúan y consolidan las 8 CBC exigidas por SUNEDU.
---

Las **8 Condiciones Básicas de Calidad (CBC)** que evalúa este módulo son las del
**Modelo de Licenciamiento Institucional**, aprobado por la Resolución del Consejo
Directivo N.° 006-2015-SUNEDU/CD de la Superintendencia Nacional de Educación Superior
Universitaria (SUNEDU), junto con las *Consideraciones para la presentación de los
medios de verificación* (Resolución de Superintendencia N.° 054-2017-SUNEDU/CD). Son
las condiciones I a VIII: las siete primeras desarrollan los aspectos mínimos que fija
el artículo 28 de la Ley 30220, Ley Universitaria, y la octava es la CBC
complementaria de transparencia. **Ese es el modelo vigente para una universidad ya
licenciada.**

La matriz de **6** condiciones que se cita a menudo pertenece a otro modelo —el de
**universidades nuevas**, Resolución del Consejo Directivo N.° 043-2020-SUNEDU/CD— y no
aplica a una universidad ya licenciada. Los modelos vigentes y los derogados están
enumerados uno por uno en la *Guía de orientación para la aplicación de la Ley 32105*
(SUNEDU, Dirección Técnico Normativa, 2024).

:::caution[Licenciamiento no es acreditación]
El **licenciamiento** lo otorga la SUNEDU, es **obligatorio** —es el permiso para
operar— y se cumple o no se cumple. La **acreditación** la otorga el Sineace (Sistema
Nacional de Evaluación, Acreditación y Certificación de la Calidad Educativa) a través
del Coneau (Consejo de Evaluación, Acreditación y Certificación de la Calidad de la
Educación Universitaria), es **voluntaria**, se valora en niveles NL/L/LP y da una
vigencia en años. El propio modelo de 2015 (§2.5) los llama «distintos y
complementarios», y precisa que el licenciamiento es condición necesaria para iniciar
la acreditación voluntaria. Mezclarlos produciría un resultado que ninguna entidad
otorga, así que el sistema lo impide: una autoevaluación rechaza un marco de
licenciamiento y un informe de cumplimiento rechaza un marco de acreditación.
:::

En el modelo de datos, cada condición es un `Elemento Marco` de tipo `Estandar` dentro
del marco normativo `CBC-SUNEDU-2026` (8 condiciones `CBC-I`..`CBC-VIII` + sus
componentes/criterios). Es el **mismo árbol normativo** que usa la autoevaluación de
acreditación — lo que cambia es el marco referenciado y, con él, su `alcance`, que es
justamente lo que activa los bloqueos del recuadro anterior.

## Por qué el diagnóstico es anual, y por qué ya no se renueva la licencia

La **Ley 32105** (*El Peruano*, 5 de agosto de 2024) modificó el artículo 13 de la Ley
Universitaria: la autorización otorgada mediante el licenciamiento «es de carácter
permanente, siempre y cuando las universidades demuestren el cumplimiento continuo de
las condiciones básicas de calidad», sujeto a evaluaciones periódicas inopinadas
(art. 13.4). **No existe un trámite de renovación periódica de licencia**: el Modelo de
Renovación de Licencia Institucional (Resolución del Consejo Directivo N.°
091-2021-SUNEDU/CD) quedó derogado por esa misma ley. Cualquier procedimiento interno
que hable de «renovar la licencia» cada cierto número de años está desactualizado.

Lo que sí exige la ley es demostrar cumplimiento **continuo**, y el párrafo 13.5 que
esa misma ley incorporó enumera las herramientas de la SUNEDU para vigilarlo:
plataforma de monitoreo y evaluación continua, auditorías públicas internas o externas,
sistema de alerta temprana, **informe anual de cumplimiento** y sanciones y
correctivos. El literal d) lo define como «la presentación de un informe anual de
cumplimiento por parte de las universidades, detallando el cumplimiento de las
condiciones básicas de calidad y el uso de los recursos públicos». Este módulo produce
ese informe: **uno por año**.

## Paso 1 — Crear el Informe Cumplimiento del año

El DocType **Informe Cumplimiento** tiene autoname `IAC-{año}` — **uno por año**. Al
guardarlo por primera vez:

- Si la tabla hija `condiciones` (child `Cumplimiento CBC`) está vacía, el sistema la
  **auto-puebla** con las 8 CBC del marco.

## Paso 2 — Evaluar cada condición

Para cada una de las 8 filas de `Cumplimiento CBC`, se registra si la institución
**cumple**, **cumple parcialmente** o **no cumple**, con su justificación. **Toda CBC
parcial o no cumplida exige justificación** — el sistema la bloquea si falta.

## Paso 3 — Semáforo consolidado

El informe consolida automáticamente los conteos (`n_cumple`, `n_parcial`,
`n_no_cumple`) y calcula un **semáforo** (campo read-only `semaforo`):

| Condición | Semáforo |
|---|---|
| Alguna condición No cumple | 🔴 Rojo |
| Ninguna No cumple, pero alguna Parcial | 🟡 Ámbar |
| Todas Cumple | 🟢 Verde |

## Paso 4 — Presentar a SUNEDU

El estado "Presentado a SUNEDU" está **bloqueado** mientras quede alguna CBC sin
evaluar — evita presentar un diagnóstico incompleto.

## Paso 5 — Generar el informe PDF

El informe (`Diagnostico CBC SUNEDU`) se genera con el mismo motor Chrome que el
informe de acreditación: portada institucional, semáforo global, resumen por conteo
de color, tabla de las 8 condiciones con su badge de estado y justificación, y firma
de la autoridad correspondiente.

## Relación con el resto del sistema

Una condición marcada No cumple o Parcial es candidata a generar un
[Hallazgo](../no-conformidades-mejora/) igual que un criterio de autoevaluación —
ambos comparten el mismo árbol `Elemento Marco` y el mismo flujo CAPA.
