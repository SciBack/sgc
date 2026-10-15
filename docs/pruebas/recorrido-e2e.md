---
title: Recorrido E2E principal
description: Prueba SGC de punta a punta usando actores separados.
---

## Escenario

Un programa ejecuta autoevaluación, sustenta criterios, confirma niveles, genera una brecha y la
cierra mediante CAPA; después verifica reportes y auditoría.

## Pasos

1. **System Manager:** prepara dos Programa Sede y User Permissions. Esperado: cada cuenta ve solo
   el ámbito asignado cuando el filtro está activo.
2. **DPGC:** selecciona marco/periodo y crea la autoevaluación planificada. Esperado: código y
   relaciones válidas.
3. **Responsable de Programa:** inicia, valora criterios y carga evidencia sintética. Esperado:
   avance y niveles propuestos recalculados.
4. **Miembro/Responsable:** revisa la propuesta; una cuenta autorizada confirma niveles. Esperado:
   nivel oficial y actor trazable.
5. **Responsable:** envía a revisión. **Otra cuenta DPGC** consolida y cierra. Esperado: no hay
   autoaprobación indebida.
6. **Responsable/Auditor:** registra hallazgo y lo escala cuando corresponda. Esperado: NC única y
   vinculada.
7. **Responsable/DPGC:** crea plan, ejecuta acciones y verifica eficacia. Esperado: estados,
   avance y semáforo coherentes.
8. **Auditor:** ejecuta auditoría y emite informe; DPGC cierra. Esperado: hallazgos y expediente
   navegables.
9. **DPGC/Alta dirección:** consulta informe, indicadores y revisión. Esperado: mismas cifras que
   los registros fuente.
10. **Rol ajeno:** intenta URL/API de otro ámbito. Esperado: sin datos y sin cambios parciales.

## Criterio de cierre

El E2E pasa solo si cada estado persiste, los casos negativos se rechazan, los reportes coinciden y
la evidencia no contiene información sensible.
