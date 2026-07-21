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

## Relación con otros módulos

Procesos, revisión por dirección y gobierno.

## Acciones operativas o configuración adicional

Se necesitan catálogos y periodos de medición.

## Fuente en código

DocTypes Indicador, Ficha Indicador y Valor Indicador. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

