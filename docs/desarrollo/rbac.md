# RBAC — Roles y permisos

El control de acceso institucional se define en `sgc/setup/f3b_rbac.py`, que aplica
**13 roles** + una matriz rol × DocType × permiso, más una regla especial de
permlevel para el campo oficial de nivel de acreditación.

## Los 13 roles

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
| **Lector Externo** | Evaluador de una acreditadora — **sin acceso al Desk**, solo portal acotado |
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
[Autoevaluación](../manual-uso/autoevaluacion.md).

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

**System Manager tiene `create=0` (solo lectura) por diseño** sobre los DocTypes de
negocio del SGC — los datos los crean los roles funcionales. Para probar o demostrar
el sistema, usa un usuario con un rol de comité (p. ej. `Comité de Programa`), **no**
System Manager: con System Manager no vas a poder crear autoevaluaciones, evidencias
ni documentos.
