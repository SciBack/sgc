---
title: Manual del módulo de Procesos
description: Entrar al sistema, recorrer el mapa de procesos, y crear, editar y publicar procesos, procedimientos, diagramas BPMN y fichas de caracterización.
sidebar:
  order: 1
---

Este manual es para quien mantiene los procesos de la institución: la dirección de calidad y los
dueños de proceso. Sigue el orden en que se trabaja: entrar, ubicarse en el mapa, completar cada
proceso y publicarlo.

:::tip[La regla de oro]
El sistema es **la fuente única** de los procesos. Lo que se publica aquí es lo que ve el portal
público de procesos: ya no hay que pedirle a nadie que lo copie a otra web.
:::

## 1. Entrar

1. Abra el navegador **con su correo institucional personal ya abierto**, no el de cargo. Si en ese
   navegador usa otra cuenta, abra una ventana de incógnito o un perfil distinto.
2. Vaya a la dirección del sistema y pulse **el botón de inicio de sesión institucional**, debajo
   del formulario. Si su cuenta ya está abierta, entra directo; si no, le pedirá el mismo usuario y
   contraseña de su correo.
3. Si no recuerda la contraseña de su correo, la recupera la mesa de ayuda, no el sistema de
   calidad.

Al entrar ve **Inicio**: lo que le toca a usted (tareas, decisiones pendientes, borradores) y el
menú de la izquierda con las áreas.

## 2. El área de Procesos

Menú izquierdo → **Procesos**. Tiene estas entradas:

| Entrada | Qué es |
|---|---|
| **Portada del área** | Lo pendiente del área y sus cifras |
| **Mapa de procesos** | Todos los procesos: macroprocesos, procesos y subprocesos |
| **Procedimientos** | Los procedimientos de cada proceso, con su diagrama |
| **Fichas de caracterización** | Una ficha por proceso: objetivo, alcance, entradas, salidas, indicadores… |
| **Mapa institucional** | La imagen aprobada del mapa (ver [Mapa institucional](./mapa-institucional/)) |
| **Interacciones entre procesos** | Qué entrega un proceso a otro |

### Ver el mapa como árbol

En **Mapa de procesos**, cambie la vista a **Árbol** con el selector de vistas, arriba a la
derecha. Se despliegan los niveles: macroproceso → proceso → subproceso. Haga clic en cualquiera
para abrirlo.

## 3. Un proceso

Al abrir un proceso ve:

- **Código y denominación.** Salen del mapa oficial de la institución: no se inventan.
- **Nivel BPM** (macroproceso, proceso o subproceso), **Nivel** (estratégico, clave o soporte) y
  **Proceso padre**.
- **Propietario (área)** y **Responsable (dueño de proceso)**. Rellene el responsable: sin él, los
  avisos del proceso no llegan a nadie.
- **Estado**: *Borrador*, *Vigente* u *Obsoleto*. Solo los vigentes salen en el portal público.
- **Conexiones**, al pie: todo lo que cuelga del proceso. Sus fichas, procedimientos, documentos,
  indicadores, riesgos, no conformidades, auditorías y evidencias, cada grupo con su contador y un
  **+** para crear uno nuevo ya enlazado.

### Crear, editar y retirar

- **Crear** un proceso nuevo: **Mapa de procesos → + Agregar**. Lo hace la dirección de calidad.
  Indique el proceso padre para que cuelgue en el lugar correcto del árbol.
- **Editar**: abra el proceso, cambie lo necesario y pulse **Guardar** (o Ctrl+S). Pueden editar la
  dirección de calidad, su analista y el dueño del proceso.
- **No se borra.** Un proceso que deja de existir pasa a **Obsoleto**. Así su historia, sus
  procedimientos y sus evidencias siguen consultables. Para moverlo de sitio o cambiarle el código,
  vea [Autogestión](../configuracion/autogestion/).

## 4. Procedimientos

Un procedimiento es la secuencia de tareas de un proceso. Lo elabora el dueño del proceso y lo
aprueba la dirección de calidad.

**Crear:** **Procedimientos → + Agregar**. Indique el código según la codificación de la
institución, el título y el **proceso** al que pertenece. Adjunte el documento si existe.

**El diagrama (BPMN):**

1. Adjunte el archivo `.bpmn` del procedimiento (el editor necesita uno adjunto para abrirse) y
   pulse **Editar BPMN**.
2. En el editor puede mover, añadir y renombrar cajas y flechas. Use **Importar .bpmn** para traer
   un diagrama hecho en otra herramienta y **Descargar .bpmn** para llevárselo.
3. Pulse **Guardar**. Si sale sin guardar, el editor le avisa. El diagrama se ve dibujado dentro de
   la ficha del procedimiento.

**El flujo de aprobación:**

| Estado | Quién actúa | Botón |
|---|---|---|
| Borrador | Dueño de proceso | *Enviar a revision* |
| En revisión | Dirección de calidad | *Aprobar* o *Devolver a borrador* |
| Aprobado | Dirección de calidad | *Publicar* o *Devolver a borrador* |
| Publicado | Dueño o dirección de calidad | *Nueva version*, para actualizarlo |
| Publicado | Dirección de calidad | *Derogar*, si deja de aplicarse |

Quien redactó el procedimiento no lo aprueba: el sistema lo impide aunque tenga los dos roles. Un
procedimiento publicado no se edita encima. Para cambiarlo se pulsa *Nueva version*, que lo
devuelve a borrador con la versión siguiente.

## 5. La ficha de caracterización

Hay una ficha por proceso. Recoge lo que la norma ISO 9001 (§4.4.1) pide de un proceso.

1. **Crear:** **Fichas de caracterización → + Agregar**, elija el proceso y guarde.
2. **Lo que se completa solo:** al guardar, la ficha trae lo que el sistema ya sabe del proceso:
   sus **procedimientos**, **documentos**, **riesgos** y **subprocesos**. No hay que teclearlos.
3. **Lo que se completa a mano:** objetivo, alcance, requisitos aplicables, recursos, entradas,
   salidas, indicadores y registros.
4. **Enviar a revisión.** Si falta algo, el sistema no la deja pasar y dice qué falta. Por ejemplo:
   «le falta: responsable del proceso, indicadores».
5. **El mismo flujo que el procedimiento:** el dueño la envía, la dirección de calidad la aprueba y
   la publica. El sistema **sella** quién la elaboró, quién la aprobó y la fecha de emisión; no se
   escriben a mano.

Con la ficha publicada puede imprimirla en PDF con el formato institucional (menú **Imprimir**) o
enviarla por correo.

## 6. La bitácora: qué cambió y quién lo hizo

Al pie de cada proceso, procedimiento y ficha está su **actividad**: cada cambio, con el valor
anterior, el nuevo, quién lo hizo y cuándo. También quedan los comentarios y cada cambio de estado
(enviado a revisión, aprobado, publicado). No hace falta llevar un registro aparte: el sistema
guarda el historial completo.

## 7. El portal público

El portal público de procesos se alimenta solo. Muestra:

- los procesos **Vigentes**;
- los procedimientos y fichas **Publicados**.

Lo que está en borrador o en revisión no sale. Para que algo aparezca en el portal, basta con
llevarlo hasta *Publicado* (o *Vigente*, en el caso del proceso).

## Quién puede qué

| Acción | Dirección de calidad | Analista de calidad | Dueño de proceso |
|---|---|---|---|
| Crear un proceso | Sí | — | — |
| Editar un proceso | Sí | Sí | Sí |
| Crear procedimiento o ficha | — | — | Sí |
| Enviar a revisión | — | — | Sí |
| Aprobar, publicar, derogar | Sí | — | — |
| Abrir una nueva versión | Sí | — | Sí |
| Borrar | Nadie: se pasa a *Obsoleto* o se deroga | | |

Los demás roles ven el mapa en modo consulta.
