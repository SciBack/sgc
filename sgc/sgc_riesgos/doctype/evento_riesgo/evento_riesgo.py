# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Evento de riesgo reportado por un colaborador.

Un evento de riesgo es algo que YA pasó: una caída, una pérdida de datos, un
plazo incumplido. Hasta aquí solo la DPGC podía registrarlo, materializando el
riesgo en su workflow; quien lo veía primero —el colaborador— no tenía dónde
contarlo. Aquí lo cuenta **cualquier usuario del sistema** (rol automático
«Desk User»), y ve solo lo que él mismo reportó.

Qué hace Calidad con el reporte:

1. Lo toma en evaluación.
2. Lo **confirma**, y eso abre la `No Conformidad` donde se hace el análisis de
   causas (#34) y el plan de acción (las Acciones de mejora); o lo **descarta**
   con un motivo, que recibe quien lo reportó.

Reglas, con la doctrina del resto del producto:

- Quién reportó, quién decidió y cuándo lo sella el sistema; no se teclea.
- Quien reportó no decide sobre su propio reporte. Va en el controlador porque
  `allow_self_approval` del workflow solo compara con `doc.owner` y no protege
  a Administrator.
- Lo decidido no se reescribe: tras confirmar o descartar, el relato queda como
  se evaluó.
- Confirmar no cambia el estado del riesgo: el evento es una ocurrencia, y si el
  riesgo entero se materializó lo decide la DPGC en su propio workflow.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import getdate, now_datetime, nowdate

DOCTYPE = "Evento Riesgo"

# Opción de `No Conformidad.origen_tipo` para lo que llega desde aquí.
ORIGEN_NC = "Evento de riesgo"

DECIDIDO = ("Confirmado", "Descartado")
TIPOS_NC = ("No conformidad mayor", "No conformidad menor")

# Lo que solo escribe el sistema: al decidir (evaluado_por, fecha) o al
# confirmar (la NC). Ni el formulario ni la API lo fijan.
SELLOS_DECISION = ("evaluado_por", "fecha_evaluacion", "no_conformidad")

# El relato del colaborador: no cambia una vez decidido.
RELATO = (
    "titulo", "fecha_evento", "riesgo", "proceso", "unidad_organica",
    "descripcion", "consecuencias", "acciones_inmediatas", "evidencia",
)


class EventoRiesgo(Document):
    def validate(self):
        self._sellar_reporte()
        self._proteger_sellos()
        self._validar_fecha()
        self._completar_desde_riesgo()
        self._validar_relato_congelado()
        self._validar_decision()

    def on_update(self):
        # Crea OTRO documento: va aquí y no en validate, para no dejar una NC
        # huérfana si la transición se revierte.
        if self._entra_en("Confirmado"):
            self._abrir_no_conformidad()

    # ---------------------------------------------------------------- helpers
    def _estado_anterior(self):
        anterior = self.get_doc_before_save()
        return anterior.estado if anterior else None

    def _entra_en(self, estado):
        """True solo en el guardado que MUEVE el documento a `estado`."""
        return self.estado == estado and self._estado_anterior() != estado

    # ------------------------------------------------------------ validaciones
    def _sellar_reporte(self):
        if self.is_new():
            self.reportado_por = frappe.session.user
            self.fecha_reporte = now_datetime()
            self.estado = "Reportado"

    def _proteger_sellos(self):
        """Fuera del guardado que decide, los sellos conservan su valor anterior.

        `read_only` en el JSON solo protege el formulario; por la API se podría
        llegar con un «Decidido por» tecleado.
        """
        anterior = self.get_doc_before_save()
        for campo in SELLOS_DECISION:
            self.set(campo, anterior.get(campo) if anterior else None)

    def _validar_fecha(self):
        if self.fecha_evento and getdate(self.fecha_evento) > getdate(nowdate()):
            frappe.throw(_("La fecha del evento no puede ser futura: se reporta lo que ya ocurrió."))

    def _completar_desde_riesgo(self):
        if not self.riesgo:
            return
        proceso, unidad = frappe.db.get_value("Riesgo", self.riesgo, ["proceso", "unidad_organica"]) or (None, None)
        if not self.proceso and proceso:
            self.proceso = proceso
        if not self.unidad_organica and unidad:
            self.unidad_organica = unidad

    def _validar_relato_congelado(self):
        anterior = self.get_doc_before_save()
        if not anterior or anterior.estado not in DECIDIDO:
            return
        cambiados = [c for c in RELATO if self.get(c) != anterior.get(c)]
        if cambiados or self.estado != anterior.estado:
            frappe.throw(
                _("El evento ya se {0}: no se modifica lo que se evaluó.").format(
                    _("confirmó") if anterior.estado == "Confirmado" else _("descartó")),
                title=_("Evento decidido"),
            )

    def _validar_decision(self):
        """Confirmar o descartar es una decisión: independiente, sellada y motivada."""
        if not (self._entra_en("Confirmado") or self._entra_en("Descartado")):
            return

        if frappe.session.user == self.reportado_por:
            frappe.throw(
                _("No puede decidir sobre un evento que usted mismo reportó: lo evalúa "
                  "otra persona de Calidad."),
                title=_("Decisión no independiente"),
            )

        if self.estado == "Descartado" and not (self.motivo_descarte or "").strip():
            frappe.throw(
                _("Explique por qué se descarta el evento: el motivo le llega a quien lo reportó."),
                title=_("Descarte sin motivo"),
            )

        if self.estado == "Confirmado" and self.tipo_nc not in TIPOS_NC:
            frappe.throw(_("Elija si la no conformidad es mayor o menor."))

        self.evaluado_por = frappe.session.user
        self.fecha_evaluacion = nowdate()

    # ------------------------------------------------------------ escalamiento
    def _abrir_no_conformidad(self):
        """Abre la NC del evento. Idempotente: si ya existe, la enlaza."""
        existente = self.no_conformidad or frappe.db.get_value(
            "No Conformidad", {"origen_doctype": DOCTYPE, "origen_id": self.name}, "name"
        )
        if existente:
            if self.no_conformidad != existente:
                self.db_set("no_conformidad", existente)
            return existente

        partes = [self.descripcion or ""]
        if self.consecuencias:
            partes.append(_("Consecuencias: {0}").format(self.consecuencias))
        if self.acciones_inmediatas:
            partes.append(_("Acciones inmediatas: {0}").format(self.acciones_inmediatas))

        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": _("Evento de riesgo {0}: {1}").format(self.name, self.titulo),
            "origen_doctype": DOCTYPE,
            "origen_id": self.name,
            "origen_tipo": ORIGEN_NC,
            "tipo": self.tipo_nc,
            "descripcion": "\n\n".join(partes),
            "unidad_organica": self.unidad_organica,
            "proceso": self.proceso,
            "criterio": frappe.db.get_value("Riesgo", self.riesgo, "elemento_marco") if self.riesgo else None,
            "estado": "Abierta",
            "requiere_analisis_causa": 1,
            "fecha_deteccion": self.fecha_evento or nowdate(),
        })
        # Quien confirma tiene permiso para crear la NC (DPGC y analista); se
        # respeta, como en la salida no conforme.
        nc.insert()
        self.db_set("no_conformidad", nc.name)
        return nc.name
