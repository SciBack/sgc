---
title: Autogestión
description: Mover, renombrar y reenlazar sin depender de soporte técnico.
---

Este manual es para el equipo de calidad. Reúne las operaciones que se hacen al mantener el
sistema vivo —cambiar de sitio un proceso, corregir un código, colgar un documento de otro
proceso— y que **no requieren llamar a nadie**.

Todo lo que hay aquí se hace desde la interfaz, con los permisos que el **rol de la oficina de
calidad** ya tiene: el de escritura sobre procesos, procedimientos, documentos, indicadores y
evidencias.

:::note[Quién puede usar este manual]
Hace falta el rol de la oficina de calidad. Una cuenta de **solo lectura** —la que se da, por
ejemplo, para revisar el sistema durante unas pruebas— ve los documentos pero no el menú para
renombrar ni los campos editables. Si al abrir un proceso no puede cambiar nada, lo que falta es
el rol, no un paso de este manual: pídaselo al administrador del sistema.
:::

## Antes de empezar: cómo se llaman las cosas

En este sistema **el código de un documento es su identidad**. Un proceso cuyo código es
`S04.04` se llama literalmente `S04.04` por dentro, y todo lo que lo referencia apunta a ese
código. No hay un identificador oculto detrás.

Esto tiene una consecuencia práctica que conviene entender antes de tocar nada: **cambiar el
código es renombrar el documento**. No es editar una etiqueta.

Esto aplica a procesos, procedimientos, documentos controlados, indicadores y evidencias.

## Mover un proceso dentro del mapa

Los procesos forman un árbol: macroproceso → proceso → subproceso. Mover uno significa cambiarle
el padre.

1. Abrir el proceso.
2. En el campo **Proceso padre**, elegir el nuevo padre.
3. Guardar.

El sistema recoloca la rama entera: los hijos del proceso movido van con él. No hay que tocarlos
uno a uno.

También existe la **vista de árbol** (en la lista de procesos, cambiar la vista a *Árbol*), que muestra la jerarquía completa y es la forma cómoda de
ver dónde está cada cosa antes de moverla.

:::caution[Lo que mover NO cambia]
Mover un proceso **no cambia su código**. Si `S04.04` pasa a colgar de otro macroproceso, sigue
llamándose `S04.04` aunque su código ya no case con su posición.

Si la intención es que el código refleje la nueva posición, son **dos operaciones distintas**:
mover y renombrar. Hacer solo la primera deja el mapa coherente y la codificación no.
:::

## Renombrar: cambiar el código de algo

El caso típico: un proceso se creó con un código provisional, o el mapa oficial cambió y ahora le
corresponde otro.

1. Abrir el documento.
2. Menú **⋯** (arriba a la derecha) → **Renombrar**.
3. Escribir el código nuevo.
4. Confirmar.

**El sistema actualiza solo todo lo que apuntaba al código viejo.** Los procedimientos que
colgaban del proceso, los documentos controlados asociados, los indicadores, las evidencias: todo
sigue enlazado sin tocar nada. No hay que ir documento por documento.

:::danger[La excepción: las fichas de caracterización]
La ficha de caracterización se nombra al crearse, componiendo `FICHA-` más el código del proceso.
Ese nombre **no se recompone** al renombrar el proceso.

Resultado: el enlace de la ficha al proceso queda correcto (el sistema lo actualiza), pero **la
ficha conserva el nombre viejo**. Una ficha llamada `FICHA-S04.04` puede acabar apuntando al
proceso `C13.02`.

No rompe nada —la ficha funciona y muestra los datos correctos— pero al buscarla por su nombre,
confunde.

**Qué hacer:** después de renombrar un proceso que ya tenga ficha, renombrar también la ficha,
con el mismo procedimiento, a `FICHA-` más el código nuevo. Son diez segundos, y evita que dentro
de un año nadie entienda por qué una ficha se llama como un proceso que ya no existe.
:::

### Cuándo NO renombrar

Si el documento ya está **publicado** y en uso fuera del sistema —citado en un informe, referido
en un acta, impreso y firmado— renombrarlo hace que esas referencias externas dejen de encontrar
nada. El sistema no puede avisar de eso porque no sabe qué hay fuera.

En ese caso, lo correcto suele ser crear el documento nuevo con el código correcto y marcar el
anterior como obsoleto, que es justo lo que el ciclo documental está pensado para hacer.

## Reenlazar: colgar algo de otro sitio

Cambiar de qué proceso depende un procedimiento, un documento o un indicador:

1. Abrir el documento.
2. Cambiar el campo de enlace que corresponda: **Proceso** en un procedimiento, un documento o un
   indicador; **Propietario (área)** en un proceso, para cambiar el área dueña.
3. Guardar.

El cambio queda registrado en el historial del documento, con quién lo hizo y cuándo. No hace
falta anotarlo en ningún sitio aparte.

## Todo cambio queda registrado

Cualquiera de estas operaciones deja rastro. En cada documento, la sección inferior muestra el
historial: qué campo cambió, de qué valor a cuál, quién lo hizo y cuándo.

Esto importa por dos razones. La primera es de auditoría: ante «¿quién cambió esto?», la respuesta
está en el propio documento. La segunda es más cotidiana: si algo se movió por error, el historial
dice exactamente cómo estaba antes.

## Lo que no se hace desde aquí

Hay operaciones que el rol de calidad **no puede** hacer, y no por descuido: afectan a cómo
funciona el sistema entero, así que quedan reservadas al administrador. Si una hace falta, se
pide:

| Operación | Por qué no |
|---|---|
| Borrar un proceso con hijos o con documentos colgando | Deja huérfano todo lo que dependía de él |
| Crear campos o cambiar formularios | Cambia el sistema para todo el mundo, no solo para quien lo hace |
| Cambiar roles y permisos | Puede dejar a alguien sin poder entrar, y eso no se ve hasta que esa persona lo intenta |
| Modificar los flujos de aprobación | Altera quién puede aprobar qué |

Borrar, en particular, no está al alcance del rol de calidad en ningún documento. Lo que ya no
sirve se retira por su ciclo —un documento pasa a *Obsoleto*, un proceso deja de estar
*Vigente*— y así conserva su historial, que es lo que una auditoría pide ver.

## Si algo sale mal

**Regla primera: no repetir la operación.** Si un cambio no surtió el efecto esperado, repetirlo
suele empeorarlo.

1. Mirar el historial del documento: dice cómo estaba antes.
2. Si el cambio fue reciente y está claro, deshacerlo poniendo el valor anterior.
3. Si afecta a varios documentos o no está claro qué pasó, pedir ayuda **antes** de seguir
   tocando. Un cambio equivocado se arregla; diez encadenados, no siempre.
