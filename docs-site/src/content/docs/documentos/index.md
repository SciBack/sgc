---
title: Manual del módulo de Documentos
description: Crear, revisar, aprobar, publicar y mantener vigentes los documentos controlados de la institución, y controlar quién los consulta.
sidebar:
  order: 1
---

Este manual es para quien elabora, revisa y aprueba documentos: los dueños de proceso, la
dirección de calidad y la autoridad que firma la aprobación final. Sigue el orden en que vive un
documento: se crea, se revisa, se publica, se mantiene vigente y, cuando hace falta, se cambia o se
retira.

:::tip[La regla de oro]
Un documento **publicado no se edita encima**. Para cambiarlo se abre una versión nueva, que pasa
otra vez por revisión y aprobación. Así siempre se sabe qué versión estaba vigente y quién la
aprobó.
:::

## 1. El área de Documentos

Menú izquierdo → **Documentos**. Tiene estas entradas:

| Entrada | Qué es |
|---|---|
| **Portada del área** | Atajos a lo pendiente: borradores, documentos de sus procesos, en revisión, por publicar y publicados |
| **Documentos controlados** | Todos los documentos, con su estado y versión |
| **Carpetas documentales** | El árbol de carpetas en que la institución ordena sus documentos |
| **Accesos a documentos** | Quién consultó o descargó cada documento (solo dirección de calidad) |

## 2. Crear un documento

1. **Documentos controlados → + Agregar**, o **Nuevo documento** en la portada del área.
2. Complete:
   - **Título** y **Tipo de documento** (obligatorios): manual, política, procedimiento,
     instructivo, guía, formato, plan, informe o documentación externa.
   - **Proceso** al que pertenece. El **dueño del proceso** se toma de ahí: no se escribe.
   - **Archivo**: el documento en sí. Sin archivo no se puede enviar a revisión.
   - Si quiere, **Tema** (del vocabulario institucional) y **Carpeta**.
3. **Guardar.** Si no escribió un código, el sistema lo genera: `PROCESO-SIGLA-NNN`, con un
   correlativo que no se repite aunque se retire un documento intermedio.

Al guardar, la ficha muestra la **vista previa** del archivo, para revisarlo sin descargarlo.

### Documentación externa

Para lo que no se guarda en el sistema, como una norma publicada en un sitio oficial, use el tipo
**Documentación externa**. En lugar de archivo lleva un **Enlace al documento externo**, que debe
empezar por `http://` o `https://`. Se controla igual que cualquier otro documento (versión,
revisión, aprobación, publicación) y su código lleva la sigla **DE**.

## 3. El flujo de aprobación

| Estado | Quién actúa | Botón |
|---|---|---|
| Borrador | Dueño de proceso | *Enviar a revision* |
| En revisión | Dirección de calidad | *Aprobar* u *Observar* |
| Observado | Dueño de proceso | *Corregir*, que lo devuelve a borrador |
| Aprobado | Autoridad aprobadora | *Publicar* |
| Aprobado | Dirección de calidad | *Observar*, si encuentra algo antes de publicar |
| Publicado | Dueño de proceso o dirección de calidad | *Nueva version*, para cambiarlo |
| Publicado | Dirección de calidad | *Derogar*, si deja de aplicarse |

**Observar exige escribir la observación.** Al pulsar *Observar*, el sistema pide la
**observación del revisor**; sin texto no deja continuar. Cada observación queda en el
**Registro de observaciones** de la ficha, con quién la hizo, cuándo, en qué paso y sobre qué
versión. Ese registro no se puede editar: es la evidencia de que el documento se revisó.

**Nadie se aprueba a sí mismo.** Quien creó el documento no puede aprobarlo ni publicarlo, aunque
tenga los dos roles: el sistema lo impide.

## 4. Publicar y difundir

Al publicarse, el documento:

- queda **vigente por un año**: la fecha aparece en **Próxima revisión**;
- se **avisa por correo** a quien lo elaboró, revisó y aprobó, a la dirección de calidad, al
  dueño del proceso y a las personas que ponga en **Difundir también a** (la gente a quien afecta
  el cambio). El aviso lleva el archivo adjunto, salvo que el documento sea de solo consulta;
- si en **Reemplaza a** indicó otro documento, ese anterior pasa solo a **Obsoleto**. No hay que
  derogarlo a mano.

## 5. Cambiar un documento publicado

1. Abra el documento publicado y pulse **Nueva version**.
2. Vuelve a **Borrador** con el número de versión siguiente, y las firmas de la versión anterior
   se vacían.
3. Antes de enviarlo a revisión, escriba la **Descripción del cambio**: el sistema no deja
   versionar en silencio.
4. Siga el mismo flujo de aprobación. Al publicarse, el cambio queda en el **Historial de
   cambios** de la ficha.

La versión nueva es el **mismo documento** vuelto a borrador: mientras no se publique otra vez, deja
de mostrarse en el portal público. Prepare el cambio antes de abrir la versión, para que ese hueco
dure lo mínimo.

## 6. Mantenerlo vigente

**Quince días antes** de la fecha de próxima revisión, el dueño del proceso (o, si no lo hay,
quien elaboró el documento) recibe una **tarea** en sus pendientes y un aviso por correo.

- **Si sigue siendo válido:** pulse **Registrar revisión sin cambios**. Puede escribir una
  conclusión. El sistema deja constancia en el historial, renueva la vigencia un año y cierra la
  tarea.
- **Si hay que cambiarlo:** abra una **Nueva version**. Al publicarse, cierra la tarea.

Pueden registrar la revisión el dueño del proceso, quien lo elaboró, la dirección de calidad y su
analista.

## 7. Documentos de solo consulta

Marque **Solo consulta en pantalla** en un documento que la gente deba leer pero no llevarse, por
ejemplo un manual interno. Entonces:

- **quien puede editarlo** (quien lo elabora o lo administra) lo ve y lo descarga como siempre;
- **quien solo puede leerlo** lo ve en el visor de la ficha, pero no le aparece el botón
  *Descargar*, el enlace directo al archivo le da error, y si descarga varios archivos juntos, el
  paquete sale sin él;
- el aviso de publicación sale **sin el adjunto**.

Exige que el archivo sea **PDF o imagen** y **privado**. Si no lo es, el sistema no deja guardar y
dice qué falta.

:::caution[Es un freno, no una caja fuerte]
Quien ve el documento en pantalla puede fotografiarlo o capturarlo. Lo que garantiza el sistema
es que no entrega el archivo y que **cada consulta queda registrada**.
:::

## 8. Enviar un documento por correo

Un documento **publicado** se envía con **Enviar por correo**, a usuarios del sistema o a
cualquier dirección, también de fuera de la institución. El archivo va adjunto, salvo en los de
solo consulta, que salen solo con el enlace. El envío queda en la actividad del documento. Pueden
hacerlo la dirección de calidad, su analista y el dueño del proceso.

## 9. Ordenar y relacionar

- **Carpetas.** Además del proceso, cada documento puede ir en una carpeta del árbol **Carpetas
  documentales**. La institución lo organiza como quiera; lo mantiene la dirección de calidad.
- **Documentos relacionados.** En la ficha, la tabla del mismo nombre enlaza el documento con
  otros y dice cómo: lo referencia, lo complementa, deriva de él o es un formato suyo.

## 10. La lista maestra

La lista maestra de documentos (código, título, tipo, versión, estado, próxima revisión y
proceso) se saca desde la propia lista:

1. En **Documentos controlados**, cambie la vista a **Reporte** con el selector de vistas, arriba
   a la derecha.
2. Filtre si lo necesita (por ejemplo, *Estado = Publicado*) y elija las columnas con
   **Seleccionar columnas**.
3. En el menú de la vista, pulse **Exportar** y elija Excel.

Es el entregable que suele pedir un auditor externo para comprobar el control documental.

## 11. Quién consultó qué

El informe **Accesos a documentos** junta cada vez que alguien abrió un documento en el visor,
lo descargó desde la ficha o lo bajó por su enlace directo, con el usuario y la fecha. Se filtra
por documento, persona y fechas. Lo ven la dirección de calidad y su analista.

## Quién puede qué

| Acción | Dirección de calidad | Analista de calidad | Dueño de proceso | Autoridad aprobadora |
|---|---|---|---|---|
| Crear un documento | Sí | Sí | Sí | — |
| Enviar a revisión, corregir | — | — | Sí | — |
| Aprobar, observar | Sí | — | — | — |
| Publicar | — | — | — | Sí |
| Abrir una nueva versión | Sí | — | Sí | — |
| Derogar | Sí | — | — | — |
| Registrar la revisión de vigencia | Sí | Sí | Sí | — |
| Ver el informe de accesos | Sí | Sí | — | — |
| Borrar | Nadie: se deroga o se reemplaza | | | |

Los demás roles consultan los documentos y pueden exportar la lista.
