---
title: Documento controlado
description: Prueba funcional completa del flujo Documento controlado.
---

## Quién puede ejecutarlo

Dueño de Proceso, DPGC y Autoridad Aprobadora.

## Precondiciones

Documento con código, versión, responsable y archivo/enlace documental disponible. Usa identificadores ficticios y cuentas separadas cuando intervengan aprobación o cierre.

## Pasos y resultados esperados

1. En estado **Borrador**, inicia sesión como **Dueño de Proceso** y ejecuta **Enviar a revision**. Resultado esperado: el registro queda en **En revision** y la acción aparece en su historial.
2. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Observar**. Resultado esperado: el registro queda en **Observado** y la acción aparece en su historial.
3. En estado **En revision**, inicia sesión como **DPGC** y ejecuta **Aprobar**. Resultado esperado: el registro queda en **Aprobado** y la acción aparece en su historial.
4. En estado **Observado**, inicia sesión como **Dueño de Proceso** y ejecuta **Corregir**. Resultado esperado: el registro queda en **Borrador** y la acción aparece en su historial.
5. En estado **Aprobado**, inicia sesión como **DPGC** y ejecuta **Observar**. Resultado esperado: el registro queda en **Observado** y la acción aparece en su historial.
6. En estado **Aprobado**, inicia sesión como **Autoridad Aprobadora** y ejecuta **Publicar**. Resultado esperado: el registro queda en **Publicado** y la acción aparece en su historial.
7. En estado **Publicado**, inicia sesión como **DPGC** y ejecuta **Derogar**. Resultado esperado: el registro queda en **Obsoleto** y la acción aparece en su historial.
8. Con un documento en estado **Publicado**, publica un segundo documento con `reemplaza_a` apuntando al primero. Resultado esperado: el primer documento pasa solo a **Obsoleto** (sin que nadie ejecute Derogar) y el historial registra la transición como automática, no como una acción de un usuario.

## Estados por los que pasa

**Borrador** → **En revision** → **Observado** → **Aprobado** → **Publicado** → **Obsoleto**. Las devoluciones o reaperturas se muestran en la tabla, por lo que el recorrido no siempre es lineal. Publicado también llega a Obsoleto sin ninguna acción humana: ver la fila automática.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Enviar a revision | En revision | Dueño de Proceso |
| En revision | Observar | Observado | DPGC |
| En revision | Aprobar | Aprobado | DPGC |
| Observado | Corregir | Borrador | Dueño de Proceso |
| Aprobado | Observar | Observado | DPGC |
| Aprobado | Publicar | Publicado | Autoridad Aprobadora |
| Publicado | Derogar | Obsoleto | DPGC |
| Publicado | *(automático)* Otro documento lo reemplaza | Obsoleto | Sistema |

## Documentación externa

El tipo **Documentación externa** sirve para lo que no se aloja en el SGC; por ejemplo, una
norma publicada en un sitio oficial. Se controla igual (versión, revisión, aprobación,
publicación) y tiene sigla **DE** en el código.

1. Crea un documento de tipo *Documentación externa* con **Enlace al documento externo** y
   sin archivo, y envíalo a revisión. Resultado: pasa. Con cualquier otro tipo, sin archivo, no.
2. Escribe un enlace que no empiece por `http://` o `https://`. Resultado: el guardado falla.
3. Abre la ficha. Resultado: el visor muestra el enlace al documento externo.

## Solo consulta en pantalla

Un documento con **Solo consulta en pantalla** marcado solo lo **descarga quien puede
editarlo**: quien lo elabora o lo administra. Quien solo tiene lectura lo ve en el visor de la
ficha y no obtiene el fichero:

| Vía | Quien solo lee | Quien puede editar |
|---|---|---|
| Visor de la ficha | lo ve | lo ve |
| Botón «Descargar» | no aparece | descarga |
| Enlace directo al fichero (`/private/files/…`) | sin permiso (403) | descarga |
| Descargar varios en ZIP (gestor de ficheros) | el ZIP sale sin él | lo incluye |
| Correo de publicación | sale sin adjunto | sale sin adjunto |

Exige un **archivo privado** en **PDF o imagen**. Un `.docx` no se puede ver en pantalla, y
un archivo público lo sirve el servidor web a cualquiera que tenga el enlace. El guardado lo
rechaza con un mensaje que dice qué falta.

⚠️ **Es un control disuasorio, no una protección técnica fuerte.** Quien ve el contenido
puede capturarlo. Lo que garantiza es que el sistema no entrega el fichero y que cada acceso
queda registrado.

## Registro de accesos

Cada apertura en el visor queda registrada como **Consulta** y cada descarga desde la ficha
como **Descarga**, con usuario y fecha. Las descargas por el enlace directo del fichero las
registra Frappe por su cuenta. El informe **Accesos a Documentos** (DPGC, Analista y System
Manager) une las tres fuentes y filtra por documento, usuario y fechas.

El registro vive en el `Access Log` de Frappe y dura lo que dure ese registro: Frappe no lo
purga salvo que se añada a *Log Settings → Logs To Clear*.

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. Las transiciones de control sin autoaprobación deben probarse con una cuenta distinta de quien creó el registro.

## Restricciones

No modifiques el campo de estado directamente. No uses System Manager para simular una decisión funcional. Si el registro está fuera del ámbito de User Permission, debe permanecer invisible o ser rechazado por backend.

## Casos negativos

- Ejecutar la transición con un rol distinto: debe estar ausente o ser rechazada.
- Repetir una acción desde un estado incompatible: el estado no debe cambiar.
- Omitir un dato obligatorio o relación requerida: el guardado debe fallar con mensaje accionable.
- Intentar autoaprobar una transición segregada: debe ser rechazada.

## Evidencia que debe capturarse

Captura del estado anterior, control ejecutado, estado final e historial; URL e identificador ficticio; rol utilizado; mensaje y respuesta HTTP de cada caso negativo. Oculta cookies y datos personales.

## Enviar por correo

Un documento **publicado** se puede enviar desde **Enviar por correo** a usuarios del sistema o a cualquier dirección, incluida gente de fuera. Lo pueden hacer la DPGC, su analista y el dueño del proceso. El archivo va adjunto, salvo en un documento de **solo consulta**, que sale solo con el enlace; un documento externo lleva su dirección web. El envío queda en el historial del documento y pasa por el modo de ensayo y la lista blanca del correo.

## Observaciones de los revisores

Al pulsar **Observar**, el sistema pide la **observación del revisor**: sin texto no se puede observar. Al cambiar de estado, la observación pasa al **Registro de observaciones** con quién la hizo, cuándo, en qué paso (por ejemplo, «En revision → Observado») y sobre qué versión; ese registro no se edita y sirve de evidencia de la revisión. Un comentario escrito al aprobar también queda registrado.

- Caso negativo: observar sin escribir la observación debe rechazarse.
- Caso negativo: solo prepara una observación quien tiene disponible la acción **Observar**.

## Revisión de vigencia

Un documento publicado vence un año después de publicarse. **Quince días antes**, el dueño del proceso (o, si no lo hay, quien lo elaboró) recibe una **tarea** en su lista de pendientes para revisarlo, además del aviso por correo. Si la revisión concluye que sigue siendo válido, **Registrar revisión sin cambios** deja constancia en el historial, renueva la vigencia un año y cierra la tarea. Si hay que cambiarlo, se elabora la versión nueva, que al publicarse deja obsoleta la anterior y cierra su tarea.

Registran la revisión el dueño del proceso, quien lo elaboró, la DPGC o su analista.

## Organización y relaciones

- **Carpeta**: además del proceso y el tema, cada documento se puede archivar en una carpeta del árbol **Carpetas documentales**, que la institución organiza como quiera (Calidad lo mantiene).
- **Documentos relacionados**: la tabla vincula el documento con otros e indica cómo (referencia, complementa, deriva de, formato de). Un documento no se relaciona consigo mismo ni dos veces igual.

## Difusión al publicar

El aviso de publicación, con el archivo adjunto salvo si es de solo consulta, llega a quien lo elaboró, revisó y aprobó, a la DPGC, al **dueño del proceso** (se toma del proceso) y a las personas de **Difundir también a**: a quien afecta la nueva versión.

## Relación con otros módulos

Mayan/control documental, notificaciones y auditoría de versiones.

## Acciones operativas o configuración adicional

El correo y las tareas periódicas requieren scheduler/servidor de correo configurados. Archivos o integraciones externas requieren sus servicios disponibles; su ausencia no debe reinterpretarse como una transición funcional válida.

## Fuente en código

La definición canónica está registrada en el manifiesto de cobertura y en sgc/setup. La solo consulta, el registro de accesos y la documentación externa, en `sgc/documentos.py`. No se documentan estados adicionales a los definidos por el workflow actual.

