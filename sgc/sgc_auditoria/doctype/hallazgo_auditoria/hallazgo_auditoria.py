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

from sgc.sgc_nucleo.doctype.trazabilidad.trazabilidad import sincronizar_evidencia_enlace

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
            # El estado solo se sincroniza al ACTUALIZAR: con el workflow activo
            # (f16), Frappe prohíbe que un documento nazca en un estado que no sea
            # el inicial, así que un hallazgo creado ya ligado a una NC no puede
            # insertarse directamente como "Escalado a NC". Nace "Abierto" y pasa
            # a "Escalado a NC" en el primer guardado posterior — o, mejor, por
            # `escalar_a_no_conformidad()`, que es la acción real.
            if self.estado == "Abierto" and not self.is_new():
                self.estado = "Escalado a NC"

        self._validar_escalamiento_real()
        self._sincronizar_trazabilidad()

    def _validar_escalamiento_real(self):
        """«Escalado a NC» exige que la No Conformidad exista.

        Se comprobó en producción (20-ago) que el estado podía fijarse a mano con
        el campo `no_conformidad` vacío: el hallazgo declaraba haber escalado y no
        había nada al otro lado. Eso rompe en silencio el enlace M05↔M06 que pide
        RF-B05 — el informe de auditoría cuenta un hallazgo escalado y en el
        módulo de no conformidades no aparece.

        El escalamiento de verdad lo hace `escalar_a_no_conformidad()`, que crea
        la NC y deja el vínculo; este guard solo impide afirmarlo sin haberlo hecho.
        """
        if self.estado == "Escalado a NC" and not self.no_conformidad:
            frappe.throw(
                _("Para marcar el hallazgo como «Escalado a NC» tiene que existir "
                  "la No Conformidad. Use la acción de escalamiento, que la crea "
                  "y deja el vínculo."),
                title=_("Escalamiento sin no conformidad"),
            )

    # ---------------------------------------------------------------- helpers

    def _sincronizar_trazabilidad(self):
        """Auto-sincroniza el picklist `evidencia` con Trazabilidad.

        Destino: `criterio_incumplido` (Elemento Marco) y/o `proceso` -- este
        hallazgo, a diferencia de Cumplimiento CBC, sí tiene ambos campos. Ver
        `sgc.sgc_nucleo.doctype.trazabilidad.trazabilidad.sincronizar_evidencia_enlace`.
        """
        sincronizar_evidencia_enlace(
            self.evidencia, elemento_marco=self.criterio_incumplido, proceso=self.proceso
        )

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
        self.save(ignore_permissions=True)

        # El estado se mueve por el motor de workflow, no asignándolo: así el
        # escalamiento queda en el historial como la transición que es. `validate`
        # ya lo habría puesto en "Escalado a NC" al ver la NC ligada, así que solo
        # se aplica si el motor aún lo ve en "Abierto".
        if frappe.db.get_value(self.doctype, self.name, "estado") == "Abierto":
            from frappe.model.workflow import apply_workflow

            apply_workflow(frappe.get_doc(self.doctype, self.name), "Escalar a NC")
            self.reload()

        return nc.name
