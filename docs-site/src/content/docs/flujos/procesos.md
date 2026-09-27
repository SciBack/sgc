---
title: Mapa de procesos
description: Prueba funcional del proceso Mapa de procesos.
---

## Quién puede ejecutarlo

DPGC gobierna; Dueño de Proceso mantiene sus fichas.

## Precondiciones

Estructura y proceso padre/tipo configurados.

## Pasos y resultados esperados

1. Crea/abre Proceso. Resultado: aparece en el mapa/árbol.
2. Completa ficha y procedimientos. Resultado: quedan vinculados al proceso.
3. Asocia indicadores/riesgos/documentos. Resultado: relaciones navegables.
4. Prueba otro dueño o rol de lectura. Resultado: escritura limitada por RBAC.

## Estados por los que pasa

Identificado → caracterizado → relacionado/operado. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No alterar estructura sincronizada como actor funcional; validar jerarquías y ciclos.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Distribuir la ficha por correo

Una ficha de caracterización **publicada** se distribuye desde **Enviar por correo**, a usuarios del sistema o a personal externo, en PDF. Si hay algún destinatario externo, va en el **formato público**, que cita el acto de aprobación en lugar de los nombres de quienes firman (Ley 29733).

## Relación con otros módulos

Procedimientos, indicadores, riesgos y documentos.

## Acciones operativas o configuración adicional

La sincronización técnica de estructura corresponde a System Manager.

## Fuente en código

sgc/setup/f1_procesos.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

