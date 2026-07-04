# -*- coding: utf-8 -*-
"""F3b RBAC — RBAC institucional del SGC: 13 Roles + Role Profiles + matriz de permisos.

Fuente única de la especificación: `doc/specs/sgc-frappe/insumos/G-escalamiento-rbac.md`
  - Parte B  -> catálogo de los 13 roles (naturaleza, ámbito, qué gobierna).
  - Parte C  -> mapeo Frappe: Role/Role Profile (el "qué") × User Permission sobre el árbol
                (el "sobre qué"). Este script SOLO fija el "qué" (los DocPerm por rol).
                El "sobre qué" (User Permission por usuario) NO se siembra aquí: eso lo
                hace el onboarding/MidPoint por persona (Parte E).
  - Parte D  -> matriz rol × DocType × permiso (C/R/W/S/X + permlevel). Es la ley de este script.

Principio (G Parte C): "Frappe intersecta dos ejes independientes." No se reimplementa
el motor de autorización de CISO. Aquí se cablea SOLO el eje "qué puede hacer cada Role".

Idempotente:
  - Roles: se crean si faltan (DPGC y Responsable de Programa YA existen — los creó
    f2_workflow; se respetan). desk_access=1 salvo Lector Externo.
  - DocPerm: se limpian los permisos de los roles SGC en cada DocType de la matriz y se
    re-aplican desde MATRIZ (upsert determinista) — así reejecutar tras editar la matriz
    deja el estado exacto, sin duplicar filas. Nunca se tocan roles ajenos (System Manager,
    All, Guest…) ni DocTypes fuera de la matriz.
  - Role Profiles: upsert de sus `roles`.

Manejo del permlevel 1 (G Parte D, nota final + campo real verificado):
  `Valoracion Estandar.nivel` (Link a Nivel Escala) es el nivel OFICIAL NL/L/LP y está en
  **permlevel 1** en el .json F1. La matriz de campo (fila "ValoracionEstandar"): solo
  **DPGC** y **Responsable de Programa** lo ESCRIBEN; el resto que ve el registro lo lee
  como `R°` (ve el doc, no el campo). => por cada rol con acceso a Valoracion Estandar se
  añade además un DocPerm en permlevel=1: read=1 para todos los que ven el doc, y write=1
  SOLO para DPGC y Responsable de Programa. Los `R°` de la matriz (Coord. Facultad, Miembro,
  Resp. Sede) => permlevel1 read=1, write=0 (ven el registro pero no el campo sensible).

Ejecutar (lo hace el orquestador, NO este agente):
    bench --site sgc.localhost execute sgc.setup.f3b_rbac.run
"""
import frappe
from frappe.permissions import add_permission, update_permission_property

# ===========================================================================
# 1) CATÁLOGO DE ROLES (G Parte B). System Manager (SysAdmin, fila 13) ya existe.
#    key interno -> (role_name Frappe, desk_access)
# ===========================================================================
ROLES = [
    ("DPGC",              1),  # 1  Gobierno — dueña del SGC
    ("Analista de Calidad (DPGC)", 1),  # 2  Gobierno operativo (staff DPGC)
    ("Coordinador de Calidad de Facultad", 1),  # 3
    ("Responsable de Calidad de Programa", 1),  # 4  (el "comité de Enfermería" generalizado)
    ("Miembro de Comité de Calidad", 1),  # 5
    ("Dueño de Proceso",  1),  # 6  process owner
    ("Data Steward",      1),  # 7  dueño de dato / dominio
    ("Auditor Interno",   1),  # 8  aseguramiento — crea Hallazgo, no valora
    ("Rectorado/VR (lectura)", 1),  # 9  alta dirección, solo lectura
    ("Decano/Director (lectura)", 1),  # 10 autoridad de línea, lectura de su ámbito
    ("Responsable de Sede", 1),  # 11 coordinación territorial (requiere fix #3)
    ("Lector Externo",    0),  # 12 evaluador CONEAU/par — SIN desk access (portal/acotado)
    # 13 SysAdmin = System Manager (Frappe core, no se recrea)
]

# ===========================================================================
# 2) MATRIZ rol × DocType × permiso  (G Parte D, transcrita literal).
#    Códigos de permiso: c=create r=read w=write s=submit x=cancel.
#    Solo se listan DocTypes que EXISTEN en el esqueleto y están en la matriz.
#
#    NO existen como DocType en este esqueleto (verificado): Crosswalk/CrosswalkSet,
#    RegistroAuditoria, y "Usuario/Rol/Asignacion" (identidad = User/Role de Frappe core,
#    gestionados por System Manager). => esas filas de la matriz NO se aplican aquí
#    (regla G: "si un doctype no está, no lo toques"). Ver reporte final.
#
#    Nombres reales de DocType verificados en apps/sgc/sgc/*/doctype/*.json.
#    La fila "🟦 marco" de G se expande a los 4 DocTypes reales del marco.
#    La fila "UnidadOrganica / ProgramaSede (🟩 estructura)" se expande a ambos.
# ===========================================================================

# clave de rol corta -> role_name (para escribir la matriz compacta)
DPGC   = "DPGC"
ANAL   = "Analista de Calidad (DPGC)"
CFAC   = "Coordinador de Calidad de Facultad"
RPRO   = "Responsable de Calidad de Programa"
MIEM   = "Miembro de Comité de Calidad"
DPROC  = "Dueño de Proceso"
DATA   = "Data Steward"
AUDI   = "Auditor Interno"
RECT   = "Rectorado/VR (lectura)"
DECA   = "Decano/Director (lectura)"
RSED   = "Responsable de Sede"
SYSM   = "System Manager"  # SysAdmin (core)

# Grupos de DocTypes según las filas colapsadas de G Parte D.
MARCO_DTS      = ["Marco Normativo", "Elemento Marco", "Escala Valoracion", "Nivel Escala"]
EVIDENCIA_DTS  = ["Evidencia", "Evidencia Enlace", "Trazabilidad"]
INDICADOR_DTS  = ["Indicador", "Ficha Indicador"]
ESTRUCTURA_DTS = ["Unidad Organica", "Programa Sede", "Programa"]

# MATRIZ[doctype] = { role_name: "crwsx-subset" }
# (se expanden abajo los grupos a cada DocType real)
_ROWS = {
    # --- 🟦 marco (Marco Normativo / Elemento Marco / Escala / Nivel Escala) ---
    "MARCO": {
        DPGC: "crws", ANAL: "crw", CFAC: "r", RPRO: "r", MIEM: "r", DPROC: "r",
        DATA: "r", AUDI: "r", RECT: "r", RSED: "r", SYSM: "rw",  # SysAdmin rw* = import técnico
        # DECA (Decano/Director lectura de su ámbito): la fila de marco no lo lista distinto
        # de las demás autoridades de lectura -> lectura.
        DECA: "r",
    },
    # --- Autoevaluacion ---
    "Autoevaluacion": {
        DPGC: "crwsx", ANAL: "crws", CFAC: "crws", RPRO: "crws", MIEM: "r",
        AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Valoracion Criterio ---
    "Valoracion Criterio": {
        DPGC: "rw", ANAL: "rw", CFAC: "rw", RPRO: "crw", MIEM: "crw",
        AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Valoracion Estandar (nivel oficial NL/L/LP en permlevel 1) ---
    # permlevel 0 (el registro): W para quien la matriz da W; R para los R y R°.
    # permlevel 1 (campo `nivel`): write SOLO DPGC + RPRO (ver PERMLEVEL1 abajo).
    "Valoracion Estandar": {
        DPGC: "rws", ANAL: "rw", CFAC: "rw", RPRO: "rws", MIEM: "r",
        AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Evidencia / Evidencia Enlace / Trazabilidad ---
    "EVIDENCIA": {
        DPGC: "crw", ANAL: "crw", CFAC: "rw", RPRO: "crw", MIEM: "crw",
        DPROC: "crw", DATA: "r", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Documento Controlado (Mayan) ---
    "Documento Controlado": {
        DPGC: "crws", ANAL: "crws", CFAC: "r", RPRO: "rw", MIEM: "r",
        DPROC: "crw", DATA: "r", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Valor Indicador (métricas) ---
    "Valor Indicador": {
        DPGC: "rw", ANAL: "rw", CFAC: "r", RPRO: "rw", MIEM: "r",
        DPROC: "rw", DATA: "crw", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Indicador / Ficha Indicador ---
    "INDICADOR": {
        DPGC: "crw", ANAL: "crw", CFAC: "r", RPRO: "r", MIEM: "r", DPROC: "r",
        DATA: "crw", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Hallazgo (Auditor: C R W S de auditoría; no valora ni cierra planes) ---
    "Hallazgo": {
        DPGC: "crwsx", ANAL: "crws", CFAC: "crw", RPRO: "crws", MIEM: "cr",
        DPROC: "r", DATA: "r", AUDI: "crws", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- Plan Mejora / Accion Mejora (CAPA) ---
    "Plan Mejora": {
        DPGC: "rws", ANAL: "rw", CFAC: "crw", RPRO: "crws", MIEM: "crw",
        DPROC: "crw", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    "Accion Mejora": {
        DPGC: "rws", ANAL: "rw", CFAC: "crw", RPRO: "crws", MIEM: "crw",
        DPROC: "crw", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "r",
    },
    # --- 🟩 estructura (Unidad Organica / Programa Sede / Programa) ---
    #     SysAdmin C R W S (sync MidPoint); DPGC C R W; Analista R W; resto R.
    "ESTRUCTURA": {
        DPGC: "crw", ANAL: "rw", CFAC: "r", RPRO: "r", MIEM: "r", DPROC: "r",
        DATA: "r", AUDI: "r", RECT: "r", RSED: "r", DECA: "r", SYSM: "crws",
    },
}

# Expandir grupos -> DocTypes reales.
def _build_matriz():
    m = {}
    for key, perms in _ROWS.items():
        if key == "MARCO":
            dts = MARCO_DTS
        elif key == "EVIDENCIA":
            dts = EVIDENCIA_DTS
        elif key == "INDICADOR":
            dts = INDICADOR_DTS
        elif key == "ESTRUCTURA":
            dts = ESTRUCTURA_DTS
        else:
            dts = [key]
        for dt in dts:
            m.setdefault(dt, {})
            # merge (no colisionan: cada grupo cae en DocTypes distintos)
            for role, code in perms.items():
                m[dt][role] = code
    return m

MATRIZ = _build_matriz()

# ===========================================================================
# 3) PERMLEVEL 1 de `Valoracion Estandar.nivel` (campo oficial NL/L/LP).
#    read=1 para todo rol que VE el registro; write=1 solo DPGC + RPRO.
#    (RPRO = "Responsable de Calidad de Programa"; DPGC.)
# ===========================================================================
PERMLEVEL1 = {
    "Valoracion Estandar": {
        # rol: (read, write) en permlevel 1
        DPGC: (1, 1),   # escribe el nivel oficial
        RPRO: (1, 1),   # escribe el nivel oficial (propone/aprueba)
        ANAL: (1, 0),   # ve el campo (staff DPGC) pero no lo confirma
        CFAC: (1, 0),   # R° en la matriz
        MIEM: (1, 0),   # R°
        RSED: (1, 0),   # R°
        AUDI: (1, 0),
        RECT: (1, 0),
        DECA: (1, 0),
        SYSM: (1, 0),
    },
}

# Roles gestionados por este script (los que limpiamos/re-aplicamos por DocType).
# Nunca tocamos filas de otros roles (All, Guest, System Manager en DocTypes que no
# están en su columna, etc.). System Manager SÍ se gestiona donde la matriz lo lista.
_SGC_ROLES = {r for r, _ in ROLES} | {SYSM}

# ===========================================================================
# Helpers
# ===========================================================================
_CODE2FLAG = {"c": "create", "r": "read", "w": "write", "s": "submit", "x": "cancel"}
_ALLFLAGS = ["read", "write", "create", "delete", "submit", "cancel"]


def _ensure_roles():
    creados = 0
    for role_name, desk in ROLES:
        if frappe.db.exists("Role", role_name):
            continue
        frappe.get_doc({
            "doctype": "Role",
            "role_name": role_name,
            "desk_access": desk,
            "is_custom": 1,
        }).insert(ignore_permissions=True)
        creados += 1
    return creados


def _apply_docperm(doctype, role, code, permlevel=0):
    """Crea el DocPerm (role, doctype, permlevel) y setea sus flags desde `code`.
    `code` es un subconjunto de 'crwsx'. read se fuerza si hay cualquier permiso.
    Devuelve dict de flags aplicados."""
    wanted = {flag: 0 for flag in _ALLFLAGS}
    for ch in code:
        flag = _CODE2FLAG.get(ch)
        if flag:
            wanted[flag] = 1
    if any(wanted.values()):
        wanted["read"] = 1  # todo permiso implica lectura

    # add_permission crea la fila si no existe (idempotente); no borra flags previos.
    add_permission(doctype, role, permlevel)
    # setear TODOS los flags explícitamente (0 y 1) para estado determinista.
    for flag in _ALLFLAGS:
        update_permission_property(doctype, role, permlevel, flag, wanted[flag], validate=False)
    return wanted


def _clear_sgc_perms(doctype):
    """Elimina los Custom DocPerm de los roles SGC en `doctype` (todos los permlevel),
    para re-aplicar limpio. No toca roles ajenos ni permisos estándar de otros roles."""
    for role in _SGC_ROLES:
        frappe.db.delete("Custom DocPerm", {"parent": doctype, "role": role})


# ===========================================================================
# 4) ROLE PROFILES (G Parte C — agrupan roles frecuentes)
#    Un Role Profile es un paquete reutilizable del "qué".
# ===========================================================================
ROLE_PROFILES = {
    # Comité de Programa = Responsable de Programa + Miembro de Comité (ej. Enfermería-Lima)
    "Comité de Programa": [RPRO, MIEM],
    # Coordinación Facultad
    "Coordinación Facultad": [CFAC],
    # Gobierno SGC = DPGC + Analista (staff que opera el día a día institucional)
    "Gobierno SGC": [DPGC, ANAL],
    # Auditoría = Auditor Interno (lee todo + crea Hallazgo)
    "Auditoría": [AUDI],
    # Lectura Institucional = Rectorado/VR (tableros globales, sin edición)
    "Lectura Institucional": [RECT],
}


def _ensure_role_profiles():
    n = 0
    for name, roles in ROLE_PROFILES.items():
        rows = [{"role": r} for r in roles]
        if frappe.db.exists("Role Profile", name):
            rp = frappe.get_doc("Role Profile", name)
            rp.set("roles", rows)
            rp.save(ignore_permissions=True)
        else:
            frappe.get_doc({
                "doctype": "Role Profile",
                "role_profile": name,
                "roles": rows,
            }).insert(ignore_permissions=True)
            n += 1
    return n


# ===========================================================================
# run()
# ===========================================================================
def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True

    n_roles = _ensure_roles()

    # Aplicar matriz (permlevel 0) + permlevel 1 donde aplique.
    dts_tocados = []
    n_docperms = 0
    for doctype, per_role in MATRIZ.items():
        if not frappe.db.exists("DocType", doctype):
            # DocType de la matriz que no existe en el esqueleto -> se omite (regla G).
            print(f"  [SKIP] DocType no existe: {doctype}")
            continue

        _clear_sgc_perms(doctype)

        # permlevel 0
        for role, code in per_role.items():
            if not frappe.db.exists("Role", role):
                continue
            _apply_docperm(doctype, role, code, permlevel=0)
            n_docperms += 1

        # permlevel 1 (solo Valoracion Estandar.nivel)
        for role, (rd, wr) in PERMLEVEL1.get(doctype, {}).items():
            if not frappe.db.exists("Role", role):
                continue
            # asegurar que el rol tenga acceso al doc en pl0 (si no, permlevel1 es inútil)
            if role not in per_role:
                continue
            add_permission(doctype, role, 1)
            update_permission_property(doctype, role, 1, "read", rd, validate=False)
            update_permission_property(doctype, role, 1, "write", wr, validate=False)
            n_docperms += 1

        dts_tocados.append(doctype)

    n_profiles = _ensure_role_profiles()

    # Refrescar caché de permisos.
    frappe.clear_cache()
    frappe.db.commit()

    frappe.flags.in_patch = False
    frappe.flags.in_fixtures = False

    print("=" * 60)
    print("F3b RBAC institucional — RESUMEN")
    print("=" * 60)
    print(f"  Roles creados en esta corrida : {n_roles} "
          f"(catálogo total: {len(ROLES)} + System Manager core)")
    print(f"  DocTypes con permisos aplicados: {len(dts_tocados)}")
    for dt in dts_tocados:
        print(f"      - {dt}")
    print(f"  DocPerm (role×doctype×permlevel) escritos: {n_docperms}")
    print(f"  Role Profiles nuevos: {n_profiles} (total definidos: {len(ROLE_PROFILES)})")
    print("  permlevel 1 (Valoracion Estandar.nivel): write=DPGC + "
          "Responsable de Calidad de Programa; read=roles que ven el registro.")
    return {
        "roles_creados": n_roles,
        "doctypes_aplicados": dts_tocados,
        "docperms": n_docperms,
        "role_profiles": list(ROLE_PROFILES.keys()),
    }
