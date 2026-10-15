---
title: CAPA desde hallazgos
description: Prueba funcional del proceso CAPA desde hallazgos.
---

## Quién puede ejecutarlo

Auditor/Responsable registra; DPGC y responsables procesan.

## Precondiciones

Hallazgo válido con tipo, severidad y origen.

## Pasos y resultados esperados

1. Genera un hallazgo desde el origen. Resultado: código único y relación persistida.
2. Si corresponde, escala a No Conformidad. Resultado: se crea una NC enlazada sin duplicación.
3. Crea el Plan Mejora. Resultado: plan relacionado en Borrador.
4. Añade y ejecuta acciones. Resultado: avance y semáforo del plan se recalculan.
5. Verifica eficacia. Resultado: cierre o reapertura trazable.

## Estados por los que pasa

Hallazgo → NC opcional → plan → acciones → verificación. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

Las funciones idempotentes no deben duplicar NC o planes; Auditor no cierra el plan.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Hallazgo, NC, Plan Mejora, Acción Mejora y evidencia.

## Acciones operativas o configuración adicional

Requiere secuencias/códigos y responsables configurados.

## Fuente en código

sgc/capa.py y controladores de mejora. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

