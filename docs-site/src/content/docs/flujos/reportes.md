---
title: Reportes PDF y Excel
description: Prueba funcional del proceso Reportes PDF y Excel.
---

## Quién puede ejecutarlo

Usuarios con lectura del expediente; generación según método expuesto.

## Precondiciones

Expediente completo y permisos sobre los datos fuente.

## Pasos y resultados esperados

1. Selecciona el alcance. Resultado: el reporte usa el registro elegido.
2. Genera PDF. Resultado: descarga válida, legible y consistente.
3. Si existe exportación tabular, genera Excel. Resultado: columnas/filas coinciden con pantalla.
4. Cambia a un usuario sin ámbito. Resultado: no obtiene datos ajenos.

## Estados por los que pasa

Solicitud → generación → descarga. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No aceptar HTML de error como PDF; no incluir datos de otro ámbito ni secretos en metadatos.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Autoevaluación, CBC, auditoría y cumplimiento.

## Acciones operativas o configuración adicional

Motor de impresión y fuentes/plantillas deben estar disponibles.

## Fuente en código

sgc/informe.py y métodos generar_pdf. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

