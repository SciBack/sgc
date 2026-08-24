# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M14 — Tratamiento de un riesgo (ISO 31000 §6.5, ISO 9001:2015 §6.1.2).

El tratamiento es lo que modifica el riesgo; lo que queda después es el riesgo
residual. El ciclo lo gobierna el Select `estado`
(Planificado -> En ejecucion -> Implementado -> Verificado), con la vuelta
«Verificar no eficaz» que devuelve a ejecución lo que la DPGC no da por bueno.

Reglas que sostiene este controlador, todas nacidas del recorrido del
2026-08-23 sobre producción (el diagrama 14 decía cosas que el sistema no hacía):

1. Quien implementa NO verifica. Lo dice la documentación del propio proceso
   («Quien implementa el tratamiento no verifica su resultado») y es el
   principio de independencia de ISO 31000 §6.6 / ISO 19011. El
   `allow_self_approval=0` del workflow NO bastaba: Frappe solo compara
   `frappe.session.user` con `doc.owner`, no con quien ejecutó el trabajo.
2. Quién implementó y quién verificó lo sella el sistema al ENTRAR en el
   estado, no se teclea.
3. Verificar es comprobar algo: exige constancia de qué se comprobó y qué nivel
   de riesgo queda después (§6.1.2 «evaluar la eficacia de estas acciones»).
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Tratamiento Riesgo SGC").
# Se usa para exigir de forma INCREMENTAL lo que cada etapa requiere, igual que
# en No Conformidad (M05) y Programa Auditoria (M06).
ORDEN = {
    "Planificado": 0,
    "En ejecucion": 1,
    "Implementado": 2,
    "Verificado": 3,
}

# Estados del riesgo padre que ya no admiten tratamientos nuevos.
RIESGO_TERMINAL = ("Cerrado",)


class TratamientoRiesgo(Document):
    def validate(self):
        self._validar_riesgo_padre_abierto()
        self._validar_verificador_independiente()
        self._sellar_implementacion()
        self._sellar_verificacion()
        self._validar_requisitos_por_estado()

    # ---------------------------------------------------------------- helpers
    def _estado_anterior(self):
        anterior = self.get_doc_before_save()
        return anterior.estado if anterior else None

    def _entra_en(self, estado):
        """True solo en el guardado que MUEVE el documento a `estado`."""
        return self.estado == estado and self._estado_anterior() != estado

    def _vuelve_por_no_eficaz(self):
        """True en la vuelta «Verificar no eficaz»: Implementado -> En ejecucion.

        Es el único camino que retrocede en este workflow, y es tan acto de
        verificación como el que va a «Verificado»: alguien miró el tratamiento
        y concluyó que no funcionó.
        """
        return self.estado == "En ejecucion" and self._estado_anterior() == "Implementado"

    # ------------------------------------------------------------ validaciones
    def _validar_riesgo_padre_abierto(self):
        """No se cuelgan tratamientos nuevos de un riesgo ya cerrado.

        Comprobado en el recorrido del 2026-08-23: con el riesgo RSK en
        «Cerrado» —estado terminal, sin ninguna transición de salida en su
        workflow— se creó un tratamiento nuevo y se puso en ejecución sin que
        nada chistara. Quedaba trabajo vivo colgando de un riesgo que el
        expediente da por resuelto, y que ya nadie vuelve a mirar.

        Se valida SOLO en el alta: un tratamiento ya en marcha cuando el riesgo
        se cierra tiene que poder terminarse (o declararse no eficaz), porque
        «Cerrado» no tiene vuelta atrás y bloquearlo aquí lo dejaría colgado
        para siempre. Que un riesgo no debería cerrarse con tratamientos a medias
        es regla del riesgo, no de esta ficha.
        """
        if not self.is_new() or not self.riesgo:
            return

        estado_riesgo = frappe.db.get_value("Riesgo", self.riesgo, "estado")
        if estado_riesgo in RIESGO_TERMINAL:
            frappe.throw(
                _("El riesgo {0} está «{1}»: no admite tratamientos nuevos. "
                  "Si el riesgo sigue vivo, no debería estar cerrado.").format(
                    self.riesgo, estado_riesgo),
                title=_("Riesgo cerrado"),
            )

    def _validar_verificador_independiente(self):
        """Quien implementó el tratamiento no puede verificarlo.

        Lo exige la documentación del propio proceso 14 —«Quien implementa el
        tratamiento no verifica su resultado»— y es independencia elemental:
        evaluar la eficacia de una acción (ISO 9001:2015 §6.1.2) no lo hace
        quien la ejecutó.

        El workflow ya llevaba `allow_self_approval=0` en las dos salidas de
        «Implementado», y NO servía: `has_approval_access` de Frappe compara
        `frappe.session.user` con `doc.owner`, es decir con quien CREÓ la ficha.
        Comprobado en el recorrido del 2026-08-23: el Dueño de Proceso creó el
        tratamiento y puso de `responsable` a un usuario con rol DPGC; ese mismo
        usuario —el implementador— pulsó «Verificar» sobre su propio trabajo y
        el motor lo dejó pasar, porque no era el owner. El tratamiento quedó
        «Verificado» por la misma persona que lo implementó.

        Se comparan las DOS identidades porque `responsable` es tecleable hasta
        el final: `implementado_por` lo sella el sistema al marcar implementado
        (ver `_sellar_implementacion`) y es lo que impide esquivar la regla
        cambiando el responsable justo antes de verificar.
        """
        if not (self._entra_en("Verificado") or self._vuelve_por_no_eficaz()):
            return

        # Sin excepción para Administrator, a propósito: en el SGC nadie opera
        # este DocType como Administrator (todo va por rol), y la regla es del
        # proceso, no del permiso. Frappe sí exime a Administrator en
        # `has_approval_access`, y esa es otra razón por la que el workflow no
        # bastaba.
        usuario = frappe.session.user
        if usuario in (self.responsable, self.implementado_por):
            frappe.throw(
                _("No puede verificar un tratamiento que usted mismo implementó. "
                  "La verificación de eficacia la hace la DPGC, no el responsable "
                  "de la implementación."),
                title=_("Verificación no independiente"),
            )

    def _validar_requisitos_por_estado(self):
        """Cada etapa exige, de forma acumulativa, lo que esa etapa necesita.

        Sin esto el tratamiento recorría el ciclo entero vacío: se podía llegar a
        «Verificado» sin estrategia, sin descripción del control, sin
        responsable, sin plazo, sin evidencia y sin una sola palabra sobre qué
        se verificó — comprobado en el recorrido del 2026-08-23. Un tratamiento
        así no es un plan de tratamiento en el sentido de ISO 31000 §6.5.3, que
        pide justamente qué se va a hacer, quién responde y para cuándo.
        """
        nivel = ORDEN.get(self.estado, 0)

        # Desde "En ejecucion": el plan de tratamiento debe existir de verdad
        # (ISO 31000 §6.5.3: acción propuesta, responsable y plazo).
        if nivel >= 1:
            if not self.estrategia:
                frappe.throw(_("Elija la estrategia de tratamiento antes de iniciarlo."))
            if not (self.descripcion or "").strip():
                frappe.throw(_("Describa el control o plan de tratamiento antes de iniciarlo."))
            if not self.responsable:
                frappe.throw(_("Asigne un responsable del tratamiento antes de iniciarlo."))
            if not self.fecha_compromiso:
                frappe.throw(_("Fije la fecha de compromiso antes de iniciar el tratamiento."))

        # Desde "Implementado": "implementado" es un check que se marca el propio
        # implementador, así que tiene que apoyarse en algo. `evidencia` es
        # justamente "prueba de implementación del control".
        if nivel >= 2 and not self.evidencia:
            frappe.throw(
                _("Vincule la evidencia que prueba la implementación del control "
                  "antes de marcarlo implementado."),
                title=_("Sin prueba de implementación"),
            )

        # En "Verificado": la verificación tiene que decir qué comprobó y con qué
        # riesgo queda la institución después (ISO 9001:2015 §6.1.2 b, ISO 31000
        # §6.5.2). El nivel residual es, además, lo que la documentación del
        # proceso 14 dice que este proceso registra.
        if nivel >= 3:
            if not (self.resultado_verificacion or "").strip():
                frappe.throw(
                    _("Registre el resultado de la verificación: qué se comprobó y "
                      "con qué evidencia."),
                    title=_("Verificación sin constancia"),
                )
            if not self.nivel_residual:
                frappe.throw(
                    _("Registre el nivel de riesgo residual que queda tras el "
                      "tratamiento."),
                    title=_("Sin nivel residual"),
                )

        # La vuelta "Verificar no eficaz" también es un juicio: debe constar por
        # qué el tratamiento no funcionó, o el siguiente ciclo repite a ciegas.
        if self._vuelve_por_no_eficaz() and not (self.resultado_verificacion or "").strip():
            frappe.throw(
                _("Explique en el resultado de la verificación por qué el "
                  "tratamiento no fue eficaz antes de devolverlo a ejecución."),
                title=_("Devolución sin motivo"),
            )

    # ------------------------------------------------------------------ sellos
    def _sellar_implementacion(self):
        """Marcar implementado ES el acto: lo firma quien lo ejecuta.

        Se sella al ENTRAR en «Implementado» para que, tras una vuelta por «no
        eficaz», quede quien re-implementa esta vez y no el de la ronda anterior.
        Mismo patrón que `Documento Controlado`, `Programa Auditoria` y
        `No Conformidad`.
        """
        if self._entra_en("Implementado"):
            self.implementado_por = frappe.session.user
            self.fecha_implementacion = nowdate()

        # Al devolverlo a ejecución por no eficaz, el sello de implementación
        # deja de ser cierto: lo implementado no valía. Se limpia para que la
        # siguiente pasada vuelva a firmarse, y para que la regla de
        # independencia mire al implementador de ESTA ronda.
        if self._vuelve_por_no_eficaz():
            self.implementado_por = None
            self.fecha_implementacion = None

    def _sellar_verificacion(self):
        """Verificar la eficacia ES el acto: lo firma quien lo ejecuta.

        Hasta el 2026-08-23 el tratamiento pasaba de «Implementado» a
        «Verificado» sin dejar rastro de quién lo verificó ni cuándo: el estado
        cambiaba y nada más. Un auditor que abría la ficha no tenía forma de
        saber quién dio por eficaz el control.

        Se sella también en la vuelta por «no eficaz»: esa también es una
        verificación, y su resultado —negativo— tiene autor y fecha.
        """
        if self._entra_en("Verificado") or self._vuelve_por_no_eficaz():
            self.verificado_por = frappe.session.user
            self.fecha_verificacion = nowdate()
