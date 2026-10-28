---
title: Evidencias y trazabilidad
description: Cómo cargar evidencias y vincularlas a criterios o procesos vía Trazabilidad.
---

## Cargar una evidencia

Una **Evidencia** puede ser:

![Formulario de una evidencia nueva](captura:acreditacion-evidencia-nueva)

- Un **archivo** adjunto (hasta 50 MB) — el sistema autocompleta mime, tamaño y hash
  desde el `File` subido.
- Un **enlace** (`enlace_url`), cuando la evidencia vive fuera del sistema.

Se exige al menos uno de los dos (archivo o URL) para guardar. El código se genera
automáticamente (`EVD-AAAA-NNNN`).

## Cargar muchas evidencias a la vez (ZIP)

Si las evidencias ya están ordenadas en carpetas (OneDrive, Drive, una unidad compartida),
no hace falta subirlas una a una:

1. Descargue la carpeta como **ZIP**.
2. Menú **Acreditación y licenciamiento → Carga masiva de evidencias → Nuevo**.
3. Adjunte el ZIP, elija el **marco normativo** y, si aplica, el programa, el periodo, la
   unidad y el proceso. Todo eso se copia a cada evidencia creada.
4. Guarde y pulse **Validar**. La carga corre en segundo plano; al terminar, el detalle dice
   qué pasó con cada archivo.

**Cómo sabe el sistema a qué criterio va cada archivo.** Por el nombre de la carpeta más
cercana que empiece por un código del marco: `1.1 Propósitos`, `Criterio 1.1`, `C1.1`,
`E1`, `Estándar 1`, `I.1` (condiciones básicas). Si necesita precisión archivo por archivo,
ponga en el ZIP un `indice.csv` con las columnas `archivo,elemento,titulo`; el índice manda
sobre las carpetas.

**Qué se omite, sin borrar nada:** los archivos que ya están cargados (misma huella) o
repetidos dentro del ZIP, los tipos que no son documentos, imágenes, audio o vídeo, los que
superan el tamaño máximo y la basura del sistema (`__MACOSX`, `.DS_Store`, `Thumbs.db`).
Lo que no casa con ningún criterio se crea igual y queda en el detalle como «Creada sin
criterio: vincúlela a mano». Las evidencias nacen **Pendientes**: darlas por válidas sigue
siendo una decisión de la persona que revisa.

## Preparar las evidencias de un marco (por ejemplo, el IAC de Sunedu)

Cada elemento de un marco normativo (un criterio, una condición básica o una pantalla del MIAC)
puede tener una **unidad responsable**, sus **unidades de apoyo** y la **evidencia requerida**. Se
completan en la ficha del elemento (Acreditación y licenciamiento → Marcos normativos → el marco → sus elementos, en **Resumen**).

![Informe de preparación de evidencias del IAC](captura:acreditacion-preparacion-evidencias)

El informe **Preparación de evidencias (IAC)** lista, para el marco que elija, cada elemento con
su responsable, cuántas evidencias tiene vinculadas, cuántas están validadas y el avance por eje.
Para el Informe Anual de Cumplimiento se usa el marco **«Ejes Temáticos de Autoevaluación del IAC
(MIAC)»**: 8 ejes, 48 pantallas [P] y 12 formatos [F], con códigos `IAC-1.1.1`. Así, un ZIP con
carpetas «1.1.1 Modelo educativo» se carga directo a su pantalla.

Los formatos que vienen del SIU (programas, mallas, locales, plana docente) no se corrigen en el
MIAC: se revisan en el SIU antes del 1 de enero.

## Vincular la evidencia a un criterio o proceso: Trazabilidad

El vínculo real entre una Evidencia y lo que sustenta (un criterio del marco
normativo, o un proceso) es el DocType **Trazabilidad** — una relación **N:M**: una
evidencia puede sustentar varios criterios, y un criterio puede tener varias
evidencias.

Cada Trazabilidad registra:

- `tipo_vinculo`: `Cumple` / `Soporta` / `Parcial`.
- `origen`: `Directo` (la evidencia aplica tal cual) o vía crosswalk (mapeo entre
  marcos normativos distintos).
- `vigencia`: una evidencia vencida se marca automáticamente.

Se crea y gestiona desde la ficha de la Evidencia, en su pestaña **Conexiones**, no como un
campo de tabla hija.

## Consultar evidencias desde un criterio

Al valorar un criterio en la [autoevaluación](../autoevaluacion/), la interfaz muestra
las evidencias ya vinculadas a ese criterio mediante una consulta inversa sobre
Trazabilidad (código, título, badge de estado, enlace al archivo) — así el comité no
tiene que ir a buscar la evidencia en otra pantalla.

## Qué evidencia exige "Válida"

Una Evidencia solo puede marcarse como `Valida` si tiene **al menos una Trazabilidad**
— una evidencia sin ningún criterio o proceso vinculado no cuenta como válida para
efectos de acreditación.

## Consumo por el informe

El informe de acreditación (`informe.py`) lee las Trazabilidades de cada criterio para
citar sus evidencias de soporte en el PDF final — por eso toda evidencia relevante
**debe** pasar por Trazabilidad, no solo quedar cargada.
