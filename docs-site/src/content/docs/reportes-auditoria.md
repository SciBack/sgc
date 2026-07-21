---
title: Reportes y auditoría
description: Cómo validar salidas, historial y trazabilidad.
---

## Reportes

Valida PDF y cualquier exportación tabular contra registros fuente: alcance, filtros, totales,
niveles confirmados, fechas y estado. El archivo debe abrir con su tipo real; una página HTML de
error descargada con extensión PDF es FAIL.

## Auditoría funcional

Para cada transición conserva actor, fecha, acción, estado anterior/final e identificador. Revisa
que reaperturas y observaciones no borren la historia y que los roles de lectura no generen cambios.

## Prueba de ámbito

Genera el mismo reporte con una cuenta autorizada, otra de distinto Programa Sede y un rol de
lectura. Esperado: datos correctos para la primera, aislamiento para la segunda y ninguna escritura
para la tercera.

## Dependencias

PDF necesita el motor de impresión y plantillas; correo necesita workers/SMTP; archivos necesitan
almacenamiento. Registra logs correlacionables sin contenido personal ni credenciales.
