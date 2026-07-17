# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 — Informe de auditoría interna.

El informe consolida los hallazgos de UNA auditoría (Link `auditoria`, reqd):
al validarse, recuenta automáticamente los hallazgos por tipo
(n_nc_mayores / n_nc_menores / n_observaciones / n_om), autocompleta la fecha de
emisión y el emisor, y enlaza de vuelta la auditoría (`Auditoria.informe`) para
que ésta pueda pasar a "Informe emitido".

El código lo compone el controlador (autoname `field:codigo`) como IAU-{anio}-NNNN.
`presentado_en` (Link a Revisión por la Dirección) cierra el ciclo con la rama 4
(§9.3): es un insumo de la revisión por la dirección.
"""
import re

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Mapa tipo de hallazgo -> campo contador del informe.
CONTADORES = {
    "No conformidad mayor": "n_nc_mayores",
    "No conformidad menor": "n_nc_menores",
    "Observacion": "n_observaciones",
    "Oportunidad de mejora": "n_om",
}


def _siguiente_correlativo(nombres) -> int:
    """Máximo sufijo numérico de una lista de códigos + 1 (robusto a borrados)."""
    maximo = 0
    for n in nombres:
        m = re.search(r"(\d+)$", n or "")
        if m:
            maximo = max(maximo, int(m.group(1)))
    return maximo + 1


class InformeAuditoria(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si no se indicó, se compone IAU-{anio}-NNNN.
        if not self.codigo:
            self.codigo = self._generar_codigo()

    def validate(self):
        self._consolidar_hallazgos()
        if not self.fecha_emision:
            self.fecha_emision = nowdate()
        if not self.emitido_por:
            self.emitido_por = frappe.session.user

    def on_update(self):
        # Enlace de vuelta: la auditoría apunta a su informe (insumo de la
        # transición a "Informe emitido"). Se usa db_set para no re-disparar la
        # validación de la auditoría en cadena.
        if self.auditoria:
            actual = frappe.db.get_value("Auditoria", self.auditoria, "informe")
            if actual != self.name:
                frappe.db.set_value(
                    "Auditoria", self.auditoria, "informe", self.name,
                    update_modified=False,
                )

    # ---------------------------------------------------------------- helpers
    def _generar_codigo(self) -> str:
        """Código IAU-{anio}-NNNN con correlativo por año (máximo sufijo + 1)."""
        anio = nowdate()[:4]
        prefijo = f"IAU-{anio}-"
        existentes = frappe.get_all(
            "Informe Auditoria",
            filters={"name": ["like", f"{prefijo}%"]},
            pluck="name",
        )
        return f"{prefijo}{_siguiente_correlativo(existentes):04d}"

    def _consolidar_hallazgos(self):
        """Recuenta los hallazgos de la auditoría por tipo y fija los contadores."""
        if not self.auditoria:
            return

        conteo = {campo: 0 for campo in CONTADORES.values()}
        tipos = frappe.get_all(
            "Hallazgo Auditoria",
            filters={"auditoria": self.auditoria},
            pluck="tipo",
        )
        for tipo in tipos:
            campo = CONTADORES.get(tipo)
            if campo:
                conteo[campo] += 1

        self.n_nc_mayores = conteo["n_nc_mayores"]
        self.n_nc_menores = conteo["n_nc_menores"]
        self.n_observaciones = conteo["n_observaciones"]
        self.n_om = conteo["n_om"]
