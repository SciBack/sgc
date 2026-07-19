---
title: Flujos de tarea por perfil
description: Qué hace cada rol del SGC, paso a paso — quién ejecuta, quién revisa y quién aprueba en cada flujo.
sidebar:
  order: 2
---

El SGC separa dos responsabilidades a propósito: **el programa ejecuta** (valora, trata,
ejecuta) y **la DPGC revisa, aprueba y cierra**. Esta separación es la que da garantía de
calidad — quien hace el trabajo no es quien lo da por bueno. Esta página resume, para cada
perfil, cuál es su trabajo día a día.

:::note[Los flujos son workflows reales]
Los pasos con nombre en *cursiva* (p. ej. *Enviar a revisión*) son transiciones de workflow
configuradas en el sistema. Solo el rol indicado puede ejecutarlas, y solo desde el estado
correcto. No es una convención de papel: el sistema lo hace cumplir.
:::

## Los perfiles y su trabajo

### Responsable de Calidad de Programa — *el comité del programa*
Es el motor operativo — el comité de calidad de un programa académico. **Ejecuta** el trabajo de
calidad de su programa:

- **Autoevaluación:** crea la autoevaluación del programa → *Iniciar evaluación* → valora los
  criterios, sube evidencias y las vincula (trazabilidad), confirma los niveles → *Enviar a
  revisión* a la DPGC.
- **No conformidades:** *Analizar causa* → *Tratar* → *Enviar a verificación*.
- **Acciones de mejora:** *Iniciar* → *Marcar ejecutada*.

Junto con la DPGC, es uno de los dos roles que pueden **fijar el nivel oficial** de acreditación
(el resto solo lo ve).

### DPGC — *la dirección de gestión de la calidad*
Es la oficina central, dueña del SGC institucional. **Revisa, aprueba y cierra** lo que los
programas ejecutan:

- **Autoevaluación:** *Consolidar* (o *Devolver a evaluación*) → *Cerrar*.
- **No conformidades:** *Cerrar eficaz* / *Cerrar no eficaz* / *Reabrir tratamiento*.
- **Planes de mejora:** *Aprobar y ejecutar* → *Cerrar plan*; verifica cada acción como
  *eficaz* / *no eficaz*.
- **Documentos:** *Aprobar* / *Observar* / *Derogar*.

### Analista de Calidad (DPGC)
Staff operativo de la DPGC. Apoya en el mismo eje: prepara, consolida y da seguimiento, bajo la
dirección de la DPGC.

### Dueño de Proceso
Responsable de un proceso del mapa institucional. En el **control documental** redacta y mantiene
los documentos de su proceso: crea el documento (Borrador) → *Enviar a revisión*; si la DPGC lo
observa, *Corregir* y reenviar.

### Autoridad Aprobadora
La autoridad que da el visto final a un documento (p. ej. Rector o Decano). **Publica** el
documento una vez aprobado (*Publicar*: Aprobado → Publicado).

### Auditor Interno
Aseguramiento independiente. Planifica y ejecuta el **programa de auditorías** y cada
**auditoría**, registra sus hallazgos y emite el informe — dos workflows completos (ver
abajo). No valora autoevaluaciones ni cierra planes: su función es constatar, no ejecutar
ni aprobar. El cierre de la auditoría lo hace la DPGC, no el propio auditor.

### Miembro de Comité de Calidad
Integrante del comité de un programa. Colabora con el Responsable de Calidad de Programa en la
valoración y la carga de evidencias.

### Coordinador de Calidad de Facultad · Responsable de Sede
Coordinación territorial y de facultad: visibilidad y articulación entre los programas de su
ámbito y la DPGC.

## Los flujos completos

Cada flujo es una máquina de estados; la tabla indica **quién** ejecuta cada paso.

### Autoevaluación de acreditación
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar evaluación | En curso | Responsable de Calidad de Programa |
| En curso | Enviar a revisión | En revisión | Responsable de Calidad de Programa |
| En revisión | Devolver a evaluación | En curso | DPGC |
| En revisión | Consolidar | Consolidada | DPGC |
| Consolidada | Cerrar | Cerrada | DPGC |

### No conformidad (CAPA)
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Abierta | Analizar causa | En análisis | Responsable de Calidad de Programa |
| En análisis | Tratar | En tratamiento | Responsable de Calidad de Programa |
| En tratamiento | Enviar a verificación | En verificación | Responsable de Calidad de Programa |
| En verificación | Cerrar eficaz | Cerrada eficaz | DPGC |
| En verificación | Cerrar no eficaz | Cerrada no eficaz | DPGC |
| En verificación | Reabrir tratamiento | En tratamiento | DPGC |

### Plan de mejora
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Aprobar y ejecutar | En ejecución | DPGC |
| En ejecución | Devolver a borrador | Borrador | DPGC |
| En ejecución | Cerrar plan | Cerrado | DPGC |

### Acción de mejora
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar | En ejecución | Responsable de Calidad de Programa |
| En ejecución | Marcar ejecutada | Ejecutada | Responsable de Calidad de Programa |
| Ejecutada | Verificar eficaz | Verificada eficaz | DPGC |
| Ejecutada | Verificar no eficaz | Verificada no eficaz | DPGC |
| Verificada no eficaz | Reabrir | En ejecución | DPGC |

### Control documental
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Enviar a revisión | En revisión | Dueño de Proceso |
| En revisión | Observar | Observado | DPGC |
| En revisión | Aprobar | Aprobado | DPGC |
| Observado | Corregir | Borrador | Dueño de Proceso |
| Aprobado | Observar | Observado | DPGC |
| Aprobado | Publicar | Publicado | Autoridad Aprobadora |
| Publicado | Derogar | Obsoleto | DPGC |

### Programa de Auditoría
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Borrador | Aprobar programa | Aprobado | DPGC |
| Aprobado | Iniciar ejecución | En ejecución | Auditor Interno |
| Aprobado | Devolver a borrador | Borrador | DPGC |
| En ejecución | Cerrar programa | Cerrado | DPGC |

### Auditoría
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar auditoría | En ejecución | Auditor Interno |
| En ejecución | Marcar ejecutada | Ejecutada | Auditor Interno |
| Ejecutada | Emitir informe | Informe emitido | Auditor Interno |
| Ejecutada | Devolver a ejecución | En ejecución | Auditor Interno |
| Informe emitido | Cerrar auditoría | Cerrada | DPGC |
| Informe emitido | Reabrir | Ejecutada | DPGC |

El cierre lo hace la DPGC, no el propio auditor — es el punto de independencia de
auditoría (ISO 19011): si una misma persona tuviera ambos roles, no podría cerrar su
propia auditoría (ver `allow_self_approval` en [RBAC](/sgc/desarrollo/rbac/)).

### Aplicación de Instrumento (M12, encuestas)
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Iniciar campo | En campo | Responsable de Calidad de Programa |
| En campo | Devolver a planificada | Planificada | DPGC |
| En campo | Cerrar aplicación | Cerrada | DPGC |

### Revisión por la Dirección
| Desde | Acción | Hacia | Rol |
|---|---|---|---|
| Planificada | Realizar revisión | Realizada | DPGC |
| Realizada | Devolver a planificada | Planificada | DPGC |
| Realizada | Cerrar revisión | Cerrada | DPGC |
| Cerrada | Reabrir revisión | Realizada | DPGC |

Las 4 transiciones las gobierna en exclusiva la DPGC (preside la revisión por la
dirección, ISO 9001 §9.3) — es la única excepción del sistema donde la autoaprobación
queda permitida a propósito, documentada como riesgo residual: ver
[RBAC](/sgc/desarrollo/rbac/).

## Quién puede crear cada cosa

Los permisos de creación no dependen del workflow sino del RBAC. En resumen:

- **Los datos de calidad los crean los roles funcionales**, no un administrador. Un *System
  Manager* tiene, a propósito, solo lectura sobre los DocTypes de negocio.
- El **nivel oficial de acreditación** (permlevel 1) solo lo escriben **DPGC** y **Responsable
  de Calidad de Programa**; los demás roles pueden verlo pero no cambiarlo.

Para el detalle técnico del modelo de permisos, ver [RBAC](/sgc/desarrollo/rbac/).
