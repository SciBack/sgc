---
title: Cálculo y confirmación de niveles
description: Prueba funcional del proceso Cálculo y confirmación de niveles.
---

## Quién puede ejecutarlo

Responsable de Programa valora; DPGC/comité autorizado confirma.

## Precondiciones

Autoevaluación con marco, estándares, criterios y escala NL/L/LP.

## Pasos y resultados esperados

1. Registra valoraciones de criterios. Resultado: el motor recalcula propuestas.
2. Ejecuta el recálculo. Resultado: cada estándar tiene nivel_propuesto y avance.
3. Revisa la propuesta sin tratarla como oficial. Resultado: confirmado permanece falso.
4. Confirma el nivel con el actor autorizado. Resultado: nivel oficial, aprobado_por y estado quedan registrados.
5. Finaliza vigencia cuando corresponda. Resultado: la propuesta consolidada queda trazable.

## Estados por los que pasa

Sin valoración → propuesta calculada → nivel confirmado → vigencia finalizada. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

LP no es una conclusión puramente mecánica; un override debe conservar justificación. Un valor propuesto no equivale a oficial.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Relación con otros módulos

Autoevaluación, Valoración Criterio, Valoración Estándar e informe.

## Acciones operativas o configuración adicional

Requiere marco y escalas correctamente cargados.

## Fuente en código

sgc/scoring.py y sgc/confirmacion.py. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

