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

Ejecutar manualmente:
    bench --site <site> execute sgc.setup.f_deploy_run_all.run
Se ejecuta también solo, vía `after_migrate` (ver hooks.py).
"""
import frappe

from sgc.setup import (
    f1_run_all, f2_run_all, f3b_rbac, f4_workflow_mejora,
    f5_workflow_documental, f6_informe_cbc, f7_notificaciones,
    f8_workflow_auditoria, f9_workflow_encuestas, f10_workflow_revision,
    f11_workflow_cumplimiento, f12_workflow_hallazgo, f13_workflow_evidencia,
    f14_workflow_riesgos,
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
]


def run():
    ok, fallidos = [], []
    for name, mod in STEPS:
        try:
            mod.run()
            frappe.db.commit()
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
