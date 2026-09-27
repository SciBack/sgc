# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Lista de verificación de auditoría — ISO 19011:2018 §6.3.4 (#32).

Es el documento de trabajo del auditor: recorre los puntos, marca cada uno como
conforme, no conforme, observación o no aplica, y anota la evidencia que vio.
De ahí salen los hallazgos. Hasta #32 ese trabajo ocurría fuera del sistema y
solo entraba el resultado.

Dos usos del mismo DocType:

- **Plantilla**: una lista SIN auditoría. Guarda las preguntas que se repiten
  cada año y siempre está en Borrador.
- **Lista aplicada**: una lista CON auditoría. Se crea desde una plantilla (o
  desde la lista de un año anterior) con `usar_en_auditoria`, que copia los
  puntos y deja los resultados vacíos.

Reglas:

1. Completar exige al menos un punto y que todos tengan resultado; si falta
   alguno, se dice cuántos.
2. Quién la completó y cuándo lo sella el sistema al entrar en «Completada».
3. Una lista de una auditoría cerrada no admite cambios: la auditoría ya
   concluyó y su expediente no se reescribe.
4. `generar_hallazgos` crea un `Hallazgo Auditoria` por cada punto «No
   conforme» u «Observación», una sola vez por punto (`Item Verificacion.hallazgo`).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

AUDITORIA_CERRADA = "Cerrada"

# Resultado del punto -> tipo del hallazgo generado. «No conforme» nace como no
# conformidad MENOR: la gravedad la decide el auditor al completar el hallazgo,
# no la lista, que solo sabe que el punto no se cumple.
RESULTADO_A_TIPO = {
    "No conforme": "No conformidad menor",
    "Observacion": "Observacion",
}


class ListaVerificacion(Document):
    def validate(self):
        self._completar_cabecera()
        self._validar_auditoria_abierta()
        self._validar_plantilla()
        self._validar_items()
        self._sellar_cierre()
        self._validar_cierre()

    def on_trash(self):
        self._validar_auditoria_abierta()

    # ---------------------------------------------------------------- helpers
    def _estado_anterior(self):
        anterior = self.get_doc_before_save()
        return anterior.estado if anterior else None

    def _es_plantilla(self):
        return not self.auditoria

    # ------------------------------------------------------------ validaciones
    def _completar_cabecera(self):
        if not self.auditor and self.is_new():
            self.auditor = frappe.session.user
        if self.estado == "En ejecucion" and not self.fecha_aplicacion:
            self.fecha_aplicacion = nowdate()
        # Lo que la lista no declara lo toma de su auditoría: es el mismo ámbito,
        # y así los hallazgos que genere nacen con proceso y unidad.
        if self.auditoria and not (self.proceso and self.unidad_organica):
            datos = frappe.db.get_value(
                "Auditoria", self.auditoria, ["proceso", "unidad_organica"], as_dict=True
            ) or {}
            self.proceso = self.proceso or datos.get("proceso")
            self.unidad_organica = self.unidad_organica or datos.get("unidad_organica")

    def _validar_auditoria_abierta(self):
        if not self.auditoria:
            return
        estado = frappe.db.get_value("Auditoria", self.auditoria, "estado")
        if estado == AUDITORIA_CERRADA:
            frappe.throw(
                _("La auditoría {0} está cerrada: su lista de verificación ya no admite "
                  "cambios.").format(self.auditoria),
                title=_("Auditoría cerrada"),
            )

    def _validar_plantilla(self):
        if self._es_plantilla() and self.estado != "Borrador":
            frappe.throw(
                _("Una lista sin auditoría es una plantilla y se queda en Borrador. "
                  "Para aplicarla, úsela en una auditoría."),
                title=_("Plantilla"),
            )

    def _validar_items(self):
        for item in self.items:
            if not (item.pregunta or "").strip():
                frappe.throw(
                    _("El punto {0} no tiene qué verificar: escriba la pregunta.").format(item.idx),
                    title=_("Punto sin pregunta"),
                )
            if not item.orden:
                item.orden = item.idx

    def _sellar_cierre(self):
        """Completar la lista ES el acto: lo firma quien lo ejecuta."""
        if self.estado == "Completada" and self._estado_anterior() != "Completada":
            self.completada_por = frappe.session.user
            self.fecha_completada = nowdate()
        elif self.estado != "Completada":
            self.completada_por = None
            self.fecha_completada = None

    def _validar_cierre(self):
        if self.estado != "Completada":
            return
        if not self.items:
            frappe.throw(_("Una lista sin puntos no se puede completar."), title=_("Lista vacía"))
        faltan = [item.idx for item in self.items if not item.resultado]
        if faltan:
            frappe.throw(
                _("Faltan {0} punto(s) sin resultado (filas {1}). Marque cada uno como "
                  "conforme, no conforme, observación o no aplica.").format(
                    len(faltan), ", ".join(str(n) for n in faltan)),
                title=_("Lista incompleta"),
            )

    # ------------------------------------------------------------- plantillas
    @frappe.whitelist()
    def usar_en_auditoria(self, auditoria):
        """Crea una lista para `auditoria` con los puntos de esta, sin resultados.

        Sirve tanto desde una plantilla como desde la lista de otra auditoría: lo
        que se reutiliza son las preguntas, nunca lo que se encontró.
        """
        if not frappe.db.exists("Auditoria", auditoria):
            frappe.throw(_("La auditoría {0} no existe.").format(auditoria))

        datos = frappe.db.get_value("Auditoria", auditoria, ["proceso", "unidad_organica"], as_dict=True)
        nueva = frappe.get_doc({
            "doctype": self.doctype,
            "titulo": self.titulo,
            "auditoria": auditoria,
            "estado": "Borrador",
            "proceso": self.proceso or datos.proceso,
            "unidad_organica": self.unidad_organica or datos.unidad_organica,
            "plantilla_origen": self.name,
            "items": [
                {
                    "orden": item.orden,
                    "pregunta": item.pregunta,
                    "criterio": item.criterio,
                    "documento_controlado": item.documento_controlado,
                }
                for item in self.items
            ],
        })
        nueva.insert()
        return nueva.name

    # --------------------------------------------------------------- hallazgos
    @frappe.whitelist()
    def generar_hallazgos(self):
        """Crea un Hallazgo Auditoria por cada punto No conforme u Observación.

        Idempotente por punto: el que ya tiene hallazgo no genera otro, y se
        informa cuántos se saltaron. Los hallazgos se crean con los permisos de
        quien pulsa (levantar hallazgos es del auditor) y nacen para completarse:
        la descripción parte de la pregunta y de la evidencia vista.

        Devuelve {"creados": [...], "ya_existian": n}.
        """
        if self._es_plantilla():
            frappe.throw(_("Una plantilla no tiene auditoría: no puede generar hallazgos."))
        self._validar_auditoria_abierta()
        self.check_permission("write")

        auditoria = frappe.db.get_value(
            "Auditoria", self.auditoria, ["proceso", "unidad_organica"], as_dict=True
        )
        creados, ya_existian = [], 0
        for item in self.items:
            tipo = RESULTADO_A_TIPO.get(item.resultado)
            if not tipo:
                continue
            if item.hallazgo and frappe.db.exists("Hallazgo Auditoria", item.hallazgo):
                ya_existian += 1
                continue

            descripcion = item.pregunta
            if (item.evidencia_vista or "").strip():
                descripcion += "\n\n" + _("Evidencia vista: {0}").format(item.evidencia_vista)
            hallazgo = frappe.get_doc({
                "doctype": "Hallazgo Auditoria",
                "auditoria": self.auditoria,
                "tipo": tipo,
                "criterio_incumplido": item.criterio,
                "descripcion": descripcion,
                "proceso": self.proceso or auditoria.proceso,
                "unidad_organica": self.unidad_organica or auditoria.unidad_organica,
                "evidencia": [{"evidencia": item.evidencia}] if item.evidencia else [],
            }).insert()
            item.hallazgo = hallazgo.name
            creados.append(hallazgo.name)

        if creados:
            self.save()

        if creados or ya_existian:
            frappe.msgprint(
                _("Hallazgos creados: {0}. Ya generados antes: {1}.").format(len(creados), ya_existian),
                alert=True,
            )
        return {"creados": creados, "ya_existian": ya_existian}
