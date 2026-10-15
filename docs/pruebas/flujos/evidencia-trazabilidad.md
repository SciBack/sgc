---
title: Evidencia y trazabilidad
description: Prueba funcional del proceso Evidencia y trazabilidad.
---

## Quién puede ejecutarlo

Roles con create/write sobre Evidencia; revisores con lectura/validación.

## Precondiciones

Objeto origen existente y archivo o enlace permitido.

## Pasos y resultados esperados

1. Crea evidencia vinculada a su origen. Resultado: obtiene código y cargado_por.
2. Añade relaciones de trazabilidad. Resultado: origen y evidencia se consultan en ambos sentidos.
3. Cambia o vence la evidencia. Resultado: las vistas reflejan vigencia/estado.
4. Consulta desde otro rol autorizado. Resultado: ve la misma relación sin editar campos reservados.

## Estados por los que pasa

Registro → vínculo trazable → revisión/vigencia. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No cargar datos reales sensibles; un enlace roto no debe darse por evidencia válida.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Autoevaluación, procesos, criterios, documentos y alertas.

## Acciones operativas o configuración adicional

El almacenamiento de archivos y permisos del sitio deben estar disponibles.

## Fuente en código

sgc/api.py y DocType Evidencia. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

