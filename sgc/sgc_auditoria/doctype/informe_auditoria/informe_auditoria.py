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

Revisión y aprobación (#37, ISO 19011 §6.5). Workflow «Informe Auditoria SGC»:
Borrador -> En revision -> Aprobado -> Distribuido, con la vuelta «Devolver a
borrador». Reglas del controlador, porque `allow_self_approval` solo mira al owner:

1. Enviar a revisión ES emitir: exige contenido y sella quién y cuándo.
2. No aprueba quien lo emitió, ni quien lo creó, ni nadie del equipo auditor.
3. Distribuir exige destinatarios; aprobar y distribuir los sella el sistema.
4. Un informe aprobado no cambia: ni su contenido ni sus contadores. Lo que se
   distribuye es lo que se aprobó.

Y lo que pide el pliego («enviar a aprobación antes de levantar los hallazgos»):
un hallazgo no se cierra, ni la auditoría, sin el informe aprobado
(`Hallazgo Auditoria` y `Auditoria`, ver `informe_aprobado`).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

from sgc.naming import siguiente_correlativo

# Mapa tipo de hallazgo -> campo contador del informe.
CONTADORES = {
    "No conformidad mayor": "n_nc_mayores",
    "No conformidad menor": "n_nc_menores",
    "Observacion": "n_observaciones",
    "Oportunidad de mejora": "n_om",
}

APROBADOS = ("Aprobado", "Distribuido")

# Lo que un informe aprobado ya no puede cambiar.
CONTENIDO = ("auditoria", "resumen_ejecutivo", "conclusiones", "pdf")


def informe_aprobado(auditoria):
    """True si la auditoría tiene un informe aprobado o ya distribuido."""
    if not auditoria:
        return False
    return bool(frappe.db.exists(
        "Informe Auditoria", {"auditoria": auditoria, "estado": ["in", list(APROBADOS)]}
    ))




class InformeAuditoria(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si no se indicó, se compone IAU-{anio}-NNNN.
        if not self.codigo:
            self.codigo = self._generar_codigo()

    def validate(self):
        anterior = self.get_doc_before_save()
        self._congelar_si_aprobado(anterior)
        if not (anterior and anterior.estado in APROBADOS):
            self._consolidar_hallazgos()
        if not self.fecha_emision:
            self.fecha_emision = nowdate()
        if not self.emitido_por:
            self.emitido_por = frappe.session.user
        self._controlar_transicion(anterior)

    # ------------------------------------------------------------ aprobación
    def _entra_en(self, estado, anterior):
        return self.estado == estado and (not anterior or anterior.estado != estado)

    def _congelar_si_aprobado(self, anterior):
        """Lo aprobado es lo que se distribuye: no se reescribe después."""
        if not anterior or anterior.estado not in APROBADOS:
            return
        cambiados = [c for c in CONTENIDO if self.get(c) != anterior.get(c)]
        if cambiados:
            frappe.throw(
                _("El informe está {0}: su contenido ya no se puede modificar ({1}).").format(
                    anterior.estado.lower(), ", ".join(cambiados)),
                title=_("Informe aprobado"),
            )

    def _controlar_transicion(self, anterior):
        """Exigencias y sellos de cada paso. Solo al PASAR: una carga que aterriza
        en un estado avanzado no es un acto de nadie (misma doctrina que el resto)."""
        if not anterior:
            return
        usuario = frappe.session.user

        if self._entra_en("En revision", anterior):
            if not ((self.conclusiones or "").strip() or (self.resumen_ejecutivo or "").strip()):
                frappe.throw(_("Redacte el resumen ejecutivo o las conclusiones antes de enviar el "
                               "informe a revisión."), title=_("Informe vacío"))
            # Emitir ES el acto: lo firma quien lo envía, también tras una devolución.
            self.emitido_por = usuario
            self.fecha_emision = nowdate()

        if self.estado == "Borrador" and anterior.estado == "En revision":
            if not (self.observaciones_revision or "").strip():
                frappe.throw(_("Explique en las observaciones qué hay que corregir antes de "
                               "devolver el informe."), title=_("Devolución sin motivo"))

        if self._entra_en("Aprobado", anterior):
            self._validar_aprobador_independiente(usuario)
            self.aprobado_por = usuario
            self.fecha_aprobacion = nowdate()

        if self._entra_en("Distribuido", anterior):
            if not (self.destinatarios or "").strip():
                frappe.throw(_("Indique a quién se distribuye el informe."),
                             title=_("Sin destinatarios"))
            self.distribuido_por = usuario
            self.fecha_distribucion = nowdate()

    def _validar_aprobador_independiente(self, usuario):
        """Aprobar es revisar el trabajo de otro (ISO 19011 §6.5.1).

        Se compara con quien lo emitió (sellado), quien lo creó y el equipo
        auditor de la auditoría: cualquiera de ellos tiene interés en darlo por
        bueno. Sin excepción para Administrator: la regla es del proceso.
        """
        equipo = set(frappe.get_all("Equipo Auditoria", filters={
            "parent": self.auditoria, "parenttype": "Auditoria"}, pluck="usuario"))
        if usuario in {self.owner, self.emitido_por} | equipo:
            frappe.throw(
                _("No puede aprobar un informe que usted emitió o de una auditoría en la que "
                  "participó. Lo aprueba alguien independiente del equipo auditor."),
                title=_("Aprobación no independiente"),
            )

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
        return f"{prefijo}{siguiente_correlativo(existentes):04d}"

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
