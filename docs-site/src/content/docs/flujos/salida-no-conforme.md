---
title: Salida no conforme
description: Prueba funcional completa del flujo Salida no conforme (ISO 9001 §8.7).
---

## Qué es

Una **salida no conforme** es el producto o servicio concreto que se entregó mal: un acta con notas mal cargadas, un certificado emitido con un error, una constancia fuera de plazo. **No es una no conformidad del sistema**: aquella dice que el sistema de gestión falló en un requisito; esta, que una entrega salió mal. Un caso aislado se queda aquí; si revela un fallo del sistema, se escala a no conformidad y las dos quedan enlazadas.

## Quién puede ejecutarlo

Cualquiera de estos roles la registra: Dueño de Proceso, DPGC, Analista de Calidad, Auditor Interno, Responsable y Coordinador de Calidad, Miembro de Comité. La tratan el **Dueño de Proceso** o la **DPGC**; la verifica y la cierra la **DPGC**.

## Precondiciones

Proceso del mapa al que pertenece la salida, y una evidencia del tratamiento para poder verificarlo. Usa identificadores ficticios y cuentas separadas: quien detecta, quien decide y quien verifica deben ser personas distintas en los casos que lo exigen.

## Pasos y resultados esperados

1. Crea la salida no conforme con título, origen, proceso, descripción y requisito incumplido. Resultado esperado: queda en **Detectada**, con código `SNC-AAAA-NNNNN`, la fecha de detección y quien detectó (por defecto, quien la registra).
2. Asigna el **responsable del tratamiento** y, como **Dueño de Proceso**, ejecuta **Iniciar tratamiento**. Resultado esperado: queda en **En tratamiento**.
3. Registra la **decisión** (corregir, autorizar bajo concesión, suspender la entrega o retirar lo entregado) y las **acciones tomadas**; ejecuta **Registrar tratamiento**. Resultado esperado: queda en **Tratada** y el sistema sella **Decidido por** y la fecha.
4. Vincula la **evidencia del tratamiento**, marca **Resultado comprobado** y, como **DPGC** distinta de quien trató, ejecuta **Verificar**. Resultado esperado: queda en **Verificada** y el sistema sella **Verificado por** y la fecha.
5. Como **DPGC**, ejecuta **Cerrar**. Resultado esperado: queda en **Cerrada** y se avisa a quien la detectó.

## Estados por los que pasa

**Detectada** → **En tratamiento** → **Tratada** → **Verificada** → **Cerrada**, con la devolución **Tratada** → **En tratamiento** cuando la verificación no da por bueno el tratamiento.

| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Detectada | Iniciar tratamiento | En tratamiento | Dueño de Proceso, DPGC |
| En tratamiento | Registrar tratamiento | Tratada | Dueño de Proceso, DPGC |
| Tratada | Verificar | Verificada | DPGC |
| Tratada | Devolver a tratamiento | En tratamiento | DPGC |
| Verificada | Cerrar | Cerrada | DPGC |

## Permisos

El actor necesita DocPerm sobre el DocType y el rol exacto de la transición. **Verificar** no admite autoaprobación: debe probarse con una cuenta distinta de quien creó el registro.

## Restricciones

- **La concesión no la autoriza quien detectó ni quien registró la salida.** Aceptar lo que no cumple lo decide otra persona.
- **El resultado no lo verifica quien lo trató ni quien decidió.**
- **Decidido por** y **Verificado por** los sella el sistema; lo que se escriba ahí a mano no prevalece.
- No modifiques el campo de estado directamente. No uses System Manager para simular una decisión funcional.

## Casos negativos

- Pasar a **Tratada** sin decisión o sin acciones tomadas: debe rechazarse.
- Autorizar bajo concesión sin justificación: debe rechazarse.
- Autorizar bajo concesión con la cuenta que detectó o registró la salida: debe rechazarse.
- Verificar sin marcar **Resultado comprobado** o sin evidencia: debe rechazarse.
- Verificar con la cuenta que trató o decidió: debe rechazarse.
- Devolver a tratamiento sin observaciones: debe rechazarse.
- Cerrar sin decisión: debe rechazarse.

## Evidencia que debe capturarse

Captura del estado anterior, control ejecutado, estado final e historial; URL e identificador ficticio; rol utilizado; mensaje y respuesta HTTP de cada caso negativo. Oculta cookies y datos personales.

## Relación con otros módulos

- **Escalar a no conformidad** (botón del formulario): crea una no conformidad con origen «Salida no conforme» y deja el enlace en los dos documentos. Si ya estaba escalada, no duplica.
- **Acción de mejora**: se puede vincular la acción que evita que se repita.
- **Mapa de procesos**: cada salida pertenece a un proceso.
- **Informe «Salidas No Conformes»**: agrupa por proceso y decisión, con número de salidas, cantidad afectada, abiertas, cerradas y escaladas; filtra por fechas, proceso, origen y decisión.

## Acciones operativas o configuración adicional

Los avisos por correo de cada transición salen según `Configuracion Correo` (modo de ensayo y lista blanca). Requieren scheduler y servidor de correo configurados.

## Fuente en código

`sgc/sgc_nucleo/doctype/salida_no_conforme/` (controlador), `sgc/setup/f23_workflow_salida_no_conforme.py` (workflow) y `sgc/sgc_nucleo/report/salidas_no_conformes/` (informe).
