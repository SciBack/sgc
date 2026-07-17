# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 / rama 4 — Revisión por la Dirección (ISO 9001:2015 e ISO 21001 §9.3).

La revisión por la dirección consolida las ENTRADAS del §9.3.2 (estado de
acciones previas, cambios de contexto, desempeño y eficacia del SGC, suficiencia
de recursos, eficacia frente a riesgos, oportunidades de mejora) y produce las
SALIDAS del §9.3.3 (decisiones y acciones sobre: oportunidades de mejora,
cambios en el SGC y necesidades de recursos).

`name` lo autogenera Frappe (autoname `format:RPD-{YYYY}-{##}`); el campo `codigo`
(reqd+unique) se rellena con el `name` si el usuario no lo indicó, para tener un
código legible sin duplicar la lógica de correlativo.

El ciclo de vida (Select `estado`: Planificada / Realizada / Cerrada) lo gobierna
el Workflow "Revision Direccion SGC" (sgc/setup/f10_workflow_revision.py, preside
la DPGC); este controlador solo aplica, de forma incremental, lo que cada etapa
exige — mismo enfoque que `no_conformidad.py`.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Revision Direccion SGC").
# Sirve para exigir, de forma incremental, lo que cada etapa requiere.
ORDEN = {
    "Planificada": 0,
    "Realizada": 1,
    "Cerrada": 2,
}

# Salidas/decisiones que ISO 9001:2015 §9.3.3 exige que produzca la revisión.
# Son exactamente los valores del Select `tipo_salida` de Salida Revision.
SALIDAS_REQUERIDAS = (
    "Oportunidad de mejora",
    "Cambio en el SGC",
    "Necesidad de recursos",
)

# Consolidación §9.3.2 -> §9.3.3: qué tipos de ENTRADA alimentan cada tipo de
# SALIDA obligatoria (valores reales de los Select `tipo_entrada`/`tipo_salida`).
CONSOLIDACION = {
    "Oportunidad de mejora": ["Oportunidades de mejora"],
    "Cambio en el SGC": [
        "Cambios en cuestiones externas/internas",
        "Desempeno y eficacia del SGC",
        "Eficacia de acciones frente a riesgos",
    ],
    "Necesidad de recursos": ["Suficiencia de recursos"],
}


class RevisionDireccion(Document):
    def validate(self):
        # `codigo` es reqd+unique; el `name` se autogenera (RPD-{YYYY}-{##}).
        # Si no se indicó código, se reutiliza el name como código legible.
        if not self.codigo:
            self.codigo = self.name

        nivel = ORDEN.get(self.estado, 0)

        # A partir de "Realizada": la revisión ya ocurrió -> fecha + entradas (§9.3.2).
        if nivel >= 1:
            if not self.fecha:
                self.fecha = nowdate()
            self._validar_entradas()

        # Al "Cerrar": deben existir las salidas/decisiones (§9.3.3) y el acta.
        if nivel >= 2:
            self._validar_salidas()
            if not self.pdf:
                frappe.throw(
                    _("Adjunta el acta/informe (PDF) para cerrar la revisión por la dirección.")
                )

    # ---------------------------------------------------------------- helpers
    def _validar_entradas(self):
        """§9.3.2 — debe haber al menos una entrada y cada una con su tipo."""
        if not self.entradas:
            frappe.throw(
                _("Registra al menos una entrada (§9.3.2) antes de marcar la "
                  "revisión como realizada.")
            )
        for fila in self.entradas:
            if not fila.tipo_entrada:
                frappe.throw(_("Cada entrada de la revisión debe indicar su tipo (§9.3.2)."))

    def _validar_salidas(self):
        """§9.3.3 — deben estar las 3 salidas obligatorias, con descripción y responsable."""
        if not self.salidas:
            frappe.throw(
                _("Registra las salidas/decisiones (§9.3.3) antes de cerrar la revisión.")
            )

        tipos_presentes = {(f.tipo_salida or "").strip() for f in self.salidas}
        faltantes = [t for t in SALIDAS_REQUERIDAS if t not in tipos_presentes]
        if faltantes:
            frappe.throw(
                _("La revisión no puede cerrarse: faltan las salidas obligatorias "
                  "(§9.3.3): {0}.").format(", ".join(faltantes))
            )

        for fila in self.salidas:
            if not (fila.descripcion or "").strip():
                frappe.throw(
                    _("Cada salida de la revisión debe describir la decisión o acción (§9.3.3).")
                )
            if not fila.responsable:
                frappe.throw(_("Cada salida (§9.3.3) debe tener un responsable asignado."))

    # ------------------------------------------------------------ consolidación
    @frappe.whitelist()
    def consolidar_salidas(self):
        """Genera el esqueleto de las salidas obligatorias (§9.3.3) que aún falten.

        Por cada tipo de salida requerido que no exista todavía, agrega una fila
        de Salida Revision con una descripción sembrada a partir de los resúmenes
        de las entradas (§9.3.2) que la alimentan (ver `CONSOLIDACION`). El
        responsable y la fecha de compromiso los completa luego la dirección.

        Idempotente: no duplica salidas de un tipo ya presente. Devuelve el número
        de salidas creadas.
        """
        tipos_presentes = {(f.tipo_salida or "").strip() for f in self.salidas}
        creadas = 0

        for tipo_salida in SALIDAS_REQUERIDAS:
            if tipo_salida in tipos_presentes:
                continue

            resumenes = [
                (e.resumen or "").strip()
                for e in self.entradas
                if e.tipo_entrada in CONSOLIDACION.get(tipo_salida, []) and (e.resumen or "").strip()
            ]
            descripcion = (
                "\n".join(f"- {r}" for r in resumenes)
                if resumenes
                else _("(Pendiente de decidir por la dirección)")
            )

            self.append("salidas", {
                "tipo_salida": tipo_salida,
                "descripcion": descripcion,
            })
            creadas += 1

        if creadas:
            self.save(ignore_permissions=True)

        return creadas
