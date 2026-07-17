# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 — Hallazgo de auditoría interna.

Un hallazgo pertenece SIEMPRE a una auditoría (Link `auditoria`, reqd) y
clasifica lo observado (`tipo`): no conformidad mayor/menor, observación,
oportunidad de mejora, conformidad o fortaleza.

Puente a M05 (§2): un hallazgo que constituye una no conformidad puede escalar a
un documento `No Conformidad` transversal, reutilizando el motor CAPA
(mismo enfoque que `sgc/capa.py`), con origen polimórfico Auditoria. Al escalar,
el hallazgo queda marcado (`genera_nc=1`, `no_conformidad`, estado "Escalado a NC").
"""
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Tipos de hallazgo que constituyen una no conformidad escalable a M05, con el
# `tipo` equivalente en el DocType No Conformidad (Select real de ambos .json).
TIPO_A_NC = {
    "No conformidad mayor": "No conformidad mayor",
    "No conformidad menor": "No conformidad menor",
    "Observacion": "Observacion",
    "Oportunidad de mejora": "Oportunidad de mejora",
}


def _siguiente_correlativo(nombres) -> int:
    """Máximo sufijo numérico de una lista de códigos + 1 (robusto a borrados)."""
    maximo = 0
    for n in nombres:
        m = re.search(r"(\d+)$", n or "")
        if m:
            maximo = max(maximo, int(m.group(1)))
    return maximo + 1


class HallazgoAuditoria(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si no se indicó, se compone HAU-{anio}-NNNN.
        if not self.codigo:
            self.codigo = self._generar_codigo()

    def validate(self):
        # Coherencia del estado con el escalamiento: si ya hay una No Conformidad
        # ligada, el hallazgo está escalado.
        if self.no_conformidad:
            self.genera_nc = 1
            if self.estado == "Abierto":
                self.estado = "Escalado a NC"

    # ---------------------------------------------------------------- helpers
    def _generar_codigo(self) -> str:
        """Código HAU-{anio}-NNNN con correlativo por año (máximo sufijo + 1)."""
        anio = nowdate()[:4]
        prefijo = f"HAU-{anio}-"
        existentes = frappe.get_all(
            "Hallazgo Auditoria",
            filters={"name": ["like", f"{prefijo}%"]},
            pluck="name",
        )
        return f"{prefijo}{_siguiente_correlativo(existentes):04d}"

    # ------------------------------------------------------------ escalamiento
    @frappe.whitelist()
    def escalar_a_no_conformidad(self):
        """Escala este hallazgo a un documento `No Conformidad` (origen Auditoria).

        - Solo escalan los tipos que constituyen no conformidad/observación/OM
          (una Conformidad o Fortaleza NO escala).
        - Copia descripción, criterio incumplido, unidad orgánica y proceso;
          deriva `programa_sede` desde la auditoría.
        - Marca el hallazgo: no_conformidad, genera_nc=1, estado "Escalado a NC".
        Idempotente: si ya hay `no_conformidad`, devuelve esa NC.

        Devuelve el name de la No Conformidad.
        """
        if self.no_conformidad:
            return self.no_conformidad

        tipo_nc = TIPO_A_NC.get(self.tipo)
        if not tipo_nc:
            frappe.throw(
                _("Un hallazgo de tipo «{0}» no constituye una no conformidad y no "
                  "puede escalar.").format(self.tipo or _("(sin tipo)"))
            )

        programa_sede = frappe.db.get_value("Auditoria", self.auditoria, "programa_sede")

        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": _("NC desde hallazgo {0}").format(self.codigo),
            "origen_doctype": "Auditoria",
            "origen_id": self.auditoria,
            "origen_tipo": "Auditoria",
            "tipo": tipo_nc,
            "descripcion": self.descripcion or "",
            "requisito_incumplido": self.criterio_incumplido,
            "unidad_organica": self.unidad_organica,
            "proceso": self.proceso,
            "programa_sede": programa_sede,
            "estado": "Abierta",
            "requiere_analisis_causa": 1 if tipo_nc == "No conformidad mayor" else 0,
            "fecha_deteccion": nowdate(),
        }).insert(ignore_permissions=True)

        self.no_conformidad = nc.name
        self.genera_nc = 1
        self.estado = "Escalado a NC"
        self.save(ignore_permissions=True)

        return nc.name
