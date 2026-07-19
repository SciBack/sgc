---
title: "RBAC: Roles y permisos"
description: Los 14 roles institucionales, la matriz de permisos (46 DocTypes) y el permlevel del nivel oficial de acreditación.
---

El control de acceso institucional se define en `sgc/setup/f3b_rbac.py`, que aplica
**14 roles** + una matriz rol × DocType × permiso que cubre los **46 DocTypes de
negocio** del SGC, más una regla especial de permlevel para el campo oficial de
nivel de acreditación.

:::note[Actualizado 2026-07-19]
Hasta esa fecha la matriz solo cubría 18 de los 46 DocTypes — los 28 restantes,
incluido `No Conformidad` pese a tener workflow activo, solo eran accesibles por
`System Manager`. Se extendió a los 46 y se agregó el rol "Autoridad Aprobadora"
(existía en el workflow de Control Documental sin ningún permiso — el workflow era
inejecutable). Ver también el fix de `allow_self_approval` en
[Flujos por perfil](/sgc/manual-uso/flujos-por-perfil/).
:::

## Los 14 roles

| Rol | Ámbito |
|---|---|
| **DPGC** | Gobierno — dueña del SGC institucional |
| **Analista de Calidad (DPGC)** | Gobierno operativo, staff de DPGC |
| **Coordinador de Calidad de Facultad** | Coordinación a nivel facultad |
| **Responsable de Calidad de Programa** | El "comité de programa" (p. ej. el comité de Enfermería) generalizado |
| **Miembro de Comité de Calidad** | Miembro del comité de un programa |
| **Dueño de Proceso** | Process owner del mapa de procesos |
| **Data Steward** | Dueño de dato/dominio (indicadores) |
| **Auditor Interno** | Aseguramiento — crea Hallazgo de auditoría, no valora ni cierra planes |
| **Rectorado/VR (lectura)** | Alta dirección, solo lectura |
| **Decano/Director (lectura)** | Autoridad de línea, lectura de su ámbito |
| **Responsable de Sede** | Coordinación territorial |
| **Autoridad Aprobadora** | Publica documentos aprobados y aprueba la Política de Calidad (p. ej. Rector o Decano) |
| **Lector Externo** | Evaluador de una acreditadora — **sin acceso al Desk**. Rol creado, **aún sin ningún permiso ni portal**: dárselo requiere construir primero el portal/web-form acotado, que todavía no existe en el repo |
| **System Manager** | SysAdmin (rol núcleo de Frappe, no se recrea) |

## Principio de diseño

> "Frappe intersecta dos ejes independientes": **qué** puede hacer cada rol
> (Role/Role Profile + DocPerm) y **sobre qué** (User Permission por persona, según el
> árbol organizacional). Este script solo cablea el primer eje — el segundo lo asigna
> el proceso de onboarding por persona (fuera del alcance de este repo canónico).

El script es **idempotente**: en cada corrida limpia los DocPerm de los roles SGC por
DocType y los re-aplica desde la matriz — así editar la matriz y re-ejecutar deja el
estado exacto, sin duplicar filas. Nunca toca roles ajenos (`System Manager` en
DocTypes fuera de la matriz, `All`, `Guest`) ni DocTypes no listados.

## Permlevel 1: el campo oficial de nivel de acreditación

`Valoracion Estandar.nivel` (el nivel NL/L/LP **oficial**, confirmado por humano) vive
en **permlevel 1**. Un rol puede tener acceso de lectura al *registro* (permlevel 0)
sin poder ver o escribir ese campo específico:

- **Escriben** el campo oficial: solo `DPGC` y `Responsable de Calidad de Programa`.
- **Leen** el campo (ven el valor, no pueden cambiarlo): el resto de roles que ven el
  registro.

Esto es lo que separa "el motor propone, el sistema puede mostrarlo a cualquiera" de
"solo el comité y DPGC pueden fijar el nivel oficial" — ver
[Autoevaluación](/sgc/manual-uso/autoevaluacion/).

## Role Profiles

Paquetes reutilizables de roles para asignación rápida:

| Role Profile | Roles que agrupa |
|---|---|
| Comité de Programa | Responsable de Calidad de Programa + Miembro de Comité de Calidad |
| Coordinación Facultad | Coordinador de Calidad de Facultad |
| Gobierno SGC | DPGC + Analista de Calidad (DPGC) |
| Auditoría | Auditor Interno |
| Lectura Institucional | Rectorado/VR (lectura) |

## Importante para desarrollo/pruebas

**System Manager tiene `create=0` (solo lectura) por diseño en los DocTypes que
están en la matriz** — los datos los crean los roles funcionales. Para probar o
demostrar el sistema, usa un usuario con un rol de comité (p. ej. `Comité de
Programa`), **no** System Manager: con System Manager no vas a poder crear
autoevaluaciones, evidencias ni documentos en esos DocTypes.

(Matiz técnico: en los DocType fuera de la matriz de este script, `System Manager`
conserva los permisos por defecto del `.json` del DocType, incluido `delete` —
ningún rol SGC tiene `delete` en ningún DocType de la matriz, por diseño.)

## Segregación de funciones en los workflows (`allow_self_approval`)

Los 9 workflows nativos del SGC (`f2_workflow.py`, `f4_workflow_mejora.py`,
`f5_workflow_documental.py`, `f8_workflow_auditoria.py`, `f9_workflow_encuestas.py`,
`f10_workflow_revision.py`) usan el flag nativo de Frappe `allow_self_approval` por
transición: en `0`, quien **creó** el documento no puede ejecutar esa transición
(la tiene que ejecutar otra persona con el rol permitido). Por defecto está en `0`;
se marca `1` explícitamente solo en el avance operativo del propio trabajo o en una
devolución/reapertura (que afloja un control, no lo supera). Las transiciones de
aprobación/verificación/cierre reales quedan en `0`.

**Excepción documentada:** `Revision Direccion SGC` mantiene `1` en sus 4
transiciones — las cuatro las ejecuta el rol `DPGC` en exclusiva, así que ponerlas
en `0` dejaría el workflow inejecutable (nadie más puede tocarlo). Es un riesgo
residual aceptado hasta que se decida un segundo rol aprobador (candidato natural:
`Rectorado/VR (lectura)`, promovido a coaprobador activo).
