---
title: Indicadores y mediciones
description: Prueba funcional del proceso Indicadores y mediciones.
---

## Quién puede ejecutarlo

Data Steward captura; Dueño de Proceso/DPGC consultan o mantienen según RBAC.

## Precondiciones

Indicador y Ficha Indicador configurados con periodicidad/unidad.

## Pasos y resultados esperados

1. Crea o abre la ficha. Resultado: metadatos y responsable se conservan.
2. Registra Valor Indicador para un periodo. Resultado: medición queda asociada.
3. Consulta tendencia/estado. Resultado: usa valores persistidos.
4. Intenta duplicar periodo o editar sin permiso. Resultado: validación o rechazo.

## Estados por los que pasa

Ficha → mediciones periódicas → consulta. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No inventar agregaciones no implementadas; validar unidad, periodo y ámbito.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Aviso de la próxima medición

La ficha del indicador tiene **Próxima medición** y **Días de aviso** (7 por defecto). Ese número de días antes, el responsable recibe un correo. Al registrar un valor, la próxima medición avanza un periodo según la frecuencia (mensual, trimestral, semestral o anual); para «por promoción» se fija a mano.

## Análisis de cada periodo

Si la ficha del indicador marca **Exigir el análisis de cada medición**, cada valor lleva su **análisis**: qué explica el resultado y qué se hará.

- Un valor tecleado no se guarda sin análisis.
- Un valor que llega por la ingesta del almacén de datos se guarda y deja al responsable del indicador una **tarea de análisis**, que se cierra sola al escribirlo.
- El análisis se puede escribir aunque la medición venga de la ingesta o su periodo esté cerrado, porque no cambia la medición; nada más de ese valor se puede tocar.
- **Analizado por** y la fecha los sella el sistema.

## Participación de las áreas

En la ficha, **Participación de las áreas** indica cuánto aporta cada área al indicador. Si se rellena, cada área aparece una vez y los pesos suman 100 %.

## Informe por familias

**Indicadores por familia** agrupa los indicadores por **categoría**, **marco normativo** o **proceso**. Para cada grupo da cuántos indicadores tiene, cuántos tienen medición y cómo está la última (verde, ámbar o rojo), el porcentaje en verde y un gráfico apilado. Se puede limitar a un periodo académico.

## Avisos de estado e incumplimientos de fecha

- **Medición vencida**: el día siguiente a la fecha prevista sin valor nuevo, se avisa al responsable y a la DPGC. Como la próxima medición avanza sola al registrar un valor, si la fecha sigue ahí es que no llegó.
- **Alerta de indicador**: cada alerta nueva (meta no alcanzada, sin medición, variación anómala…) avisa por correo a su responsable; si no tiene, a la DPGC.

## Relación con otros módulos

Procesos, revisión por dirección y gobierno.

## Acciones operativas o configuración adicional

Se necesitan catálogos y periodos de medición.

## Fuente en código

DocTypes Indicador, Ficha Indicador y Valor Indicador. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

