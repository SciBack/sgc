---
title: Mapa institucional
description: Cargar y publicar el cuadro aprobado del mapa de procesos, y entender el aviso de desfase.
---

El SGC guarda el mapa de procesos de dos formas distintas, y conviene no
confundirlas:

- El **árbol de procesos** (menú *Mapa de procesos*) es la estructura viva: se
  navega, se edita y es de donde salen las fichas, los indicadores y los BPMN.
- El **cuadro institucional** es la lámina que el órgano de gobierno aprobó por
  resolución, con la identidad gráfica de la institución. Es lo que está colgado
  en la pared y lo que la gente reconoce.

Esta página trata del segundo. Vive en el DocType **Mapa Procesos**.

## Por qué es una imagen y no un dibujo generado

Podría dibujarse el cuadro a partir del árbol, y así no se desactualizaría nunca.
No se hace porque el resultado se *parecería* al mapa aprobado sin *serlo*: los
colores, la disposición y la redacción de la lámina son parte de lo que se
aprobó. Un cuadro aprobado es un documento, no una vista.

## Cargar una versión

1. Ir a **Mapa Procesos** y crear un documento.
2. Rellenar la **versión** (es el identificador: `v8.0`, `2026-01`, lo que use la
   institución) y adjuntar la **imagen**.
3. Anotar **fecha de aprobación**, **aprobado por** y **resolución**. En
   *aprobado por* va el órgano —Consejo Universitario, Comité de Calidad—, no una
   persona: lo que respalda el mapa es el acuerdo, no una firma individual.
4. Dejarlo en **Borrador** mientras se prepara.

## Ponerla en vigor

Cambiar el estado a **Vigente**. Al guardar:

- El sistema exige que haya imagen y fecha de aprobación. Un "vigente" sin lámina
  no es el cuadro aprobado, es una ficha vacía ocupando su sitio.
- **La versión anterior pasa automáticamente a Obsoleto.** Solo puede haber un
  mapa en vigor: dos a la vez es la forma más rápida de que dos áreas trabajen
  con cuadros distintos creyendo que es el mismo.

Las versiones anteriores no se borran: quedan como Obsoleto y siguen
consultables, que es lo que pide una auditoría cuando pregunta con qué mapa se
trabajaba en una fecha.

## Verlo

Desde el árbol de procesos, menú **⋯ → Mapa institucional**. Se abre el cuadro
vigente con su versión, su fecha y su resolución.

## El aviso de desfase

Si el árbol de procesos ha cambiado **después** de la fecha de aprobación del
cuadro, al abrirlo aparece un aviso en naranja.

No bloquea nada, y es a propósito: un mapa aprobado sigue siendo el mapa aprobado
aunque el trabajo haya seguido avanzando por debajo. El aviso solo evita que eso
sea invisible, que es el riesgo real de guardar una imagen en vez de generarla.
Cuando aparece, la decisión es de quien gobierna el mapa: o el cambio del árbol
no afecta al cuadro, o toca preparar una versión nueva y aprobarla.

El aviso se calcula con lo que cada persona puede ver. Quien tiene el ámbito
acotado a su unidad puede no verlo aunque el árbol haya cambiado en otra: se
prefiere callar antes que delatar movimiento en unidades que esa persona no
puede consultar.

## Quién puede qué

Cargar el cuadro y ponerlo en vigor es de **DPGC** (y de administración del
sistema). Todos los demás perfiles lo ven: es justo el documento que la
institución quiere que se reconozca. Si cualquiera pudiera marcar "vigente", el
cuadro dejaría de significar "el aprobado".
