"""Orquestador de despliegue — corre TODO el setup del SGC en orden de dependencia.

Fase 1 del plan de acción (2026-07-19, hallazgo H8): antes de esto, un site nuevo
migrado con `bench migrate` quedaba SIN RBAC ni workflows — `f3b_rbac.run()` no
estaba en ningún runner ni hook, solo documentado como comentario suelto en
`instalacion.md`. El resultado: System Manager con create/read/write/delete en
los 68 DocTypes y ningún rol SGC funcional hasta que alguien corriera a mano
6+ `bench execute` en el orden correcto.

Todos los scripts de abajo son idempotentes (verifican existencia antes de
crear, o hacen upsert determinista) — reejecutar esto en cada `bench migrate`
es seguro y deja el estado exacto de la matriz/los workflows actuales, no
duplica nada.

Orden (por dependencia real, no alfabético):
  1. f1_run_all      — estructura: los 68 DocTypes (SIN esto nada más aplica)
  2. f2_run_all      — fields custom + carga CONEAU + workflows Autoevaluacion/NC
  3. f3b_rbac        — RBAC institucional (roles + matriz de permisos + role profiles)
  4. f4_workflow_mejora      — workflow Plan/Accion de Mejora
  5. f5_workflow_documental  — workflow Documento Controlado
  6. f6_informe_cbc          — Print Format Diagnóstico CBC SUNEDU
  7. f7_notificaciones       — las 4 Notification de M17 (channel queda en
                               System Notification; activar Email es config de
                               runtime, ver arquitectura-sgc.md)
  8. f8_workflow_auditoria   — workflows Programa Auditoria / Auditoria
  9. f9_workflow_encuestas   — workflow Aplicacion Instrumento
  10. f10_workflow_revision  — workflow Revision Direccion
  11. f11_workflow_cumplimiento — workflow Informe Cumplimiento (Fase 2)
  12. f12_workflow_hallazgo     — workflow Hallazgo (Fase 2)
  13. f13_workflow_evidencia    — workflow Evidencia (Fase 2)
  14. f14_workflow_riesgos      — workflows Riesgo + Tratamiento Riesgo (Fase 2)
  15. f15_notificaciones_workflow — Notification Value Change en transiciones
  16. f16_workflow_hallazgo_auditoria — workflow Hallazgo Auditoria (M06)
  17. f17_alcance_marcos — clasifica cada marco (licenciamiento / acreditación)
                               reales del workflow de Informe Cumplimiento

Ejecutar manualmente:
    bench --site <site> execute sgc.setup.f_deploy_run_all.run
Se ejecuta también solo, vía `after_migrate` (ver hooks.py).
"""
import os
import re
import time

import frappe

# Los locks de DOCUMENTO de Frappe se nombran con el hash del documento
# (frappe/utils/file_lock.py); los del framework tienen nombre legible
# (`bench_migrate`, `scheduler`…). Solo los primeros son seguros de borrar.
_ES_LOCK_DE_DOCUMENTO = re.compile(r"[0-9a-f]{16,}")

from sgc.setup import (
    f1_run_all,
    f2_run_all,
    f3b_rbac,
    f4_workflow_mejora,
    f5_workflow_documental,
    f6_informe_cbc,
    f7_notificaciones,
    f8_workflow_auditoria,
    f9_workflow_encuestas,
    f10_workflow_revision,
    f11_workflow_cumplimiento,
    f12_workflow_hallazgo,
    f13_workflow_evidencia,
    f14_workflow_riesgos,
    f15_notificaciones_workflow,
    f16_workflow_hallazgo_auditoria,
    f17_alcance_marcos,
    f18_workspace,
)

STEPS = [
    ("f1_run_all", f1_run_all),
    ("f2_run_all", f2_run_all),
    ("f3b_rbac", f3b_rbac),
    ("f4_workflow_mejora", f4_workflow_mejora),
    ("f5_workflow_documental", f5_workflow_documental),
    ("f6_informe_cbc", f6_informe_cbc),
    ("f7_notificaciones", f7_notificaciones),
    ("f8_workflow_auditoria", f8_workflow_auditoria),
    ("f9_workflow_encuestas", f9_workflow_encuestas),
    ("f10_workflow_revision", f10_workflow_revision),
    ("f11_workflow_cumplimiento", f11_workflow_cumplimiento),
    ("f12_workflow_hallazgo", f12_workflow_hallazgo),
    ("f13_workflow_evidencia", f13_workflow_evidencia),
    ("f14_workflow_riesgos", f14_workflow_riesgos),
    ("f15_notificaciones_workflow", f15_notificaciones_workflow),
    ("f16_workflow_hallazgo_auditoria", f16_workflow_hallazgo_auditoria),
    ("f17_alcance_marcos", f17_alcance_marcos),
    ("f18_workspace", f18_workspace),
]


def _correr_paso(name, mod, reintentos=2):
    """Ejecuta un paso, reintentando si el DocType quedó bloqueado por el propio migrate.

    Cuando un deploy cambia el .json de un DocType, `bench migrate` lo sincroniza y lo
    deja LOCKED/encolado. Como este orquestador corre en `after_migrate`, un paso que
    escriba sobre ese mismo DocType (típicamente `f3b_rbac`, que aplica DocPerm sobre los
    46 DocTypes de negocio) revienta con `DocumentLockedError` — y el RBAC se queda sin
    reaplicar en producción, en silencio salvo por el Error Log.

    El lock es transitorio: liberarlo y reintentar basta (verificado en el lab 2026-07-27,
    donde el paso suelto pasaba y dentro de migrate no). Se reintenta SOLO ante lock, no
    ante cualquier error: un fallo real debe seguir fallando.
    """
    for intento in range(reintentos + 1):
        try:
            mod.run()
            frappe.db.commit()
            return True
        except frappe.exceptions.DocumentLockedError:
            frappe.db.rollback()
            if intento == reintentos:
                raise
            # Los locks de documento de Frappe son ARCHIVOS en sites/<site>/locks/
            # (frappe/utils/file_lock.py), no entradas de caché. Los que deja el propio
            # migrate ya no tienen proceso detrás cuando llegamos a after_migrate, así
            # que se borran los caducados y se reintenta.
            # ⚠️ En ese MISMO directorio viven también los locks con nombre del
            # framework — sobre todo `bench_migrate.lock`, que crea
            # `frappe.utils.synchronization.filelock` y es lo que impide que dos
            # `bench migrate` corran a la vez. Borrarlo dejaría el sitio sin esa
            # protección justo durante un despliegue. Por eso NO se barre el
            # directorio: solo se borran los locks de DOCUMENTO, cuyo nombre es un
            # hash hexadecimal (`create_lock(name)` sobre el hash del doc), nunca
            # un lock con nombre legible como `bench_migrate` o `scheduler`.
            try:
                locks_dir = frappe.get_site_path("locks")
                if os.path.isdir(locks_dir):
                    for f in os.listdir(locks_dir):
                        if not f.endswith(".lock"):
                            continue
                        if not _ES_LOCK_DE_DOCUMENTO.fullmatch(f[: -len(".lock")]):
                            continue  # lock con nombre del framework: intocable
                        try:
                            os.remove(os.path.join(locks_dir, f))
                        except FileNotFoundError:
                            pass  # otro proceso lo liberó primero
            except Exception:
                pass
            time.sleep(2)
    return False


def run():
    ok, fallidos = [], []
    for name, mod in STEPS:
        try:
            _correr_paso(name, mod)
            ok.append(name)
        except Exception:
            frappe.db.rollback()
            fallidos.append(name)
            frappe.log_error(title=f"f_deploy_run_all: fallo en {name}")
            print(f"  [FALLO] {name} — ver Error Log")
    print("=" * 60)
    print("F_DEPLOY_RUN_ALL — RESUMEN")
    print("=" * 60)
    print("OK:", ", ".join(ok) if ok else "(ninguno)")
    if fallidos:
        print("FALLIDOS:", ", ".join(fallidos), "— revisar Error Log antes de continuar")
    return {"ok": ok, "fallidos": fallidos}
