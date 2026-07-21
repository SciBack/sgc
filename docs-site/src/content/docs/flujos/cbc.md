---
title: Diagnóstico CBC
description: Prueba funcional del proceso Diagnóstico CBC.
---

## Quién puede ejecutarlo

DPGC/Analista y roles de consulta autorizados.

## Precondiciones

Catálogo CBC y registros de cumplimiento cargados.

## Pasos y resultados esperados

1. Abre el diagnóstico. Resultado: aparecen las condiciones y componentes configurados.
2. Registra cumplimiento y evidencia. Resultado: se conserva por componente.
3. Recalcula/consulta el resumen. Resultado: el semáforo refleja los datos persistidos.
4. Genera el informe. Resultado: el PDF representa el mismo estado.

## Estados por los que pasa

Sin datos → evaluación registrada → resumen/informe. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No inferir cumplimiento por ausencia de datos; validar que totales y PDF coincidan.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Cumplimiento CBC, evidencias e informe.

## Acciones operativas o configuración adicional

La generación PDF requiere motor de impresión disponible.

## Fuente en código

sgc/setup/f6_informe_cbc.py y Cumplimiento CBC. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

