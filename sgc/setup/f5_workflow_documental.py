"""F5 workflow — Workflow nativo del Control Documental (M03).

Mismo patrón que f2_workflow.py / f4_workflow_mejora.py (reutiliza sus helpers).
Los estados son los valores REALES del Select `estado` de Documento Controlado:
Borrador / En revision / Aprobado / Publicado / Obsoleto / Observado.

El workflow gobierna QUIÉN puede mover el documento entre estados. Las reglas de
QUÉ debe cumplirse para moverlo (archivo adjunto, revisor, aprobador, descripción
del cambio) las impone el controlador documento_controlado.py — que es la barrera
real y no se puede saltar desde la API.

Reparto de responsabilidades (procedimiento DTN-Pro-01 de SUNEDU):
- Dueño del proceso elabora y envía a revisión.
- DPGC revisa: aprueba u observa.
- La autoridad competente publica (la firma que habilita a comunicar el documento).
- Al publicar, el controlador marca como Obsoleto el documento reemplazado.

Ejecutar (idempotente):
    bench --site <site> execute sgc.setup.f5_workflow_documental.run
"""
import frappe

from sgc.setup.f2_workflow import _ensure_role, _upsert_workflow

ROLES = ["Dueño de Proceso", "DPGC", "Autoridad Aprobadora"]

WF_DOCUMENTO = {
    "name": "Documento Controlado SGC",
    "document_type": "Documento Controlado",
    "workflow_state_field": "estado",
    "is_active": 1,
    "send_email_alert": 0,  # revertido 2026-07-19: dispara attach_print (PDF) por email en CUALQUIER save con transicion pendiente, no solo en transiciones reales -- rompio 70 tests y arriesga flood de correos en prod. Necesita diseno propio (Fase 2, item aparte), no un toggle de 1 linea.
    "states": [
        ("Borrador", "0", "Dueño de Proceso"),
        ("En revision", "0", "DPGC"),
        ("Observado", "0", "Dueño de Proceso"),
        ("Aprobado", "0", "Autoridad Aprobadora"),
        # Publicado y Obsoleto quedan bajo la DPGC: son los estados que la
        # Lista Maestra reporta hacia afuera.
        ("Publicado", "0", "DPGC"),
        ("Obsoleto", "0", "DPGC"),
    ],
    "transitions": [
        ("Borrador", "Enviar a revision", "En revision", "Dueño de Proceso", 1),  # avance operativo
        ("En revision", "Observar", "Observado", "DPGC", 1),  # devuelve, afloja
        # aprobar y publicar son el control DTN-Pro-01 -> self_approval=0 (default):
        # quien elaboró el documento no puede aprobarlo/publicarlo bajo su misma cuenta.
        ("En revision", "Aprobar", "Aprobado", "DPGC"),
        ("Observado", "Corregir", "Borrador", "Dueño de Proceso", 1),  # avance operativo
        ("Aprobado", "Observar", "Observado", "DPGC", 1),  # devuelve, afloja
        ("Aprobado", "Publicar", "Publicado", "Autoridad Aprobadora"),
        ("Publicado", "Derogar", "Obsoleto", "DPGC"),
    ],
}


def run():
    frappe.flags.in_patch = True

    for r in ROLES:
        _ensure_role(r)

    n_doc = _upsert_workflow(WF_DOCUMENTO)

    frappe.db.commit()

    print("Workflow OK:", n_doc,
          "[Borrador -> En revision -> Aprobado -> Publicado -> Obsoleto]")
    print("             (Observado devuelve a Borrador)")
