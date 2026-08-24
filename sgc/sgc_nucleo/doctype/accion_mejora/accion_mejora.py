# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document

from sgc.naming import codigo_anual

# Avance implícito por estado: los estados terminales fijan el %. En "En ejecucion"
# y "Verificada no eficaz" se respeta el % manual que registre el responsable.
ESTADO_AVANCE = {
    "Planificada": 0,
    "Ejecutada": 100,
    "Verificada eficaz": 100,
}

# Los dos estados que registran una revisión de eficacia (ISO 9001 §10.2.1 e):
# entrar en cualquiera de ellos ES el acto de verificar, lo haga quien lo haga.
VERIFICACIONES = ("Verificada eficaz", "Verificada no eficaz")


class AccionMejora(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si no se indicó, se compone AM-{anio}-NNNN.
        # Hasta el 2026-08-23 no lo componía nadie salvo `capa.py` al crearla, así
        # que crear una por cualquier otra vía fallaba con «Código is required».
        if not self.codigo:
            self.codigo = codigo_anual(self.doctype, "AM")

    def validate(self):
        anterior = self.get_doc_before_save()
        self._exigir_lo_de_cada_etapa(anterior)
        self._sellar_verificacion(anterior)
        self._fijar_avance(anterior)

    def _exigir_lo_de_cada_etapa(self, anterior):
        """Lo que cada transición del workflow exige para poder ocurrir.

        Se comprueba **al cambiar de estado**, no en cada guardado: el control es
        del ACTO (iniciar, verificar), y una carga inicial que aterriza ya en un
        estado avanzado (semilla, migración, `capa.py`) no es un acto de nadie y
        no se le puede pedir una evidencia que no existe.

        Comprobado en el recorrido del 2026-08-23 sobre producción: una acción
        creada sin responsable ni ETA recorrió Planificada -> En ejecucion ->
        Ejecutada -> Verificada eficaz sin que nada la parara, y se cerró como
        eficaz sin una sola evidencia. Los dos huecos tienen consecuencia real:

        * sin `responsable` y sin `fecha_compromiso` la acción es INVISIBLE al
          control: `Plan Mejora._calcular_semaforo` solo mira acciones con fecha
          (una sin ETA jamás pone el plan en Rojo) y el aviso «Accion de mejora
          por vencer» (f7) se dirige a `responsable` y se dispara por
          `fecha_compromiso` — sin ellos no se envía a nadie, nunca.
        * cerrar como eficaz sin `evidencia_cierre` es afirmar que la acción
          funcionó sin nada que lo respalde. ISO 9001:2015 §10.2.2 pide conservar
          información documentada de los resultados de la acción correctiva.
          Su hermana `No Conformidad` ya lo exigía; esta no.
        """
        cambio_de_estado = bool(anterior) and anterior.estado != self.estado

        if cambio_de_estado and self.estado == "En ejecucion":
            if not self.responsable:
                frappe.throw(_("Asigna un responsable antes de iniciar la acción de mejora."))
            if not self.fecha_compromiso:
                frappe.throw(
                    _("Define la fecha de compromiso (ETA) antes de iniciar la acción: "
                      "sin ella la acción no entra en el semáforo del plan ni genera aviso.")
                )

        if cambio_de_estado and self.estado == "Verificada eficaz" and not self.evidencia_cierre:
            frappe.throw(_("Adjunta la evidencia de cierre para verificar la acción como eficaz."))

        # Y una vez verificada eficaz, la evidencia no se puede quitar: el cierre
        # se quedaría sin soporte sin volver a pasar por ninguna verificación.
        if (
            anterior
            and self.estado == "Verificada eficaz"
            and anterior.evidencia_cierre
            and not self.evidencia_cierre
        ):
            frappe.throw(_("No se puede quitar la evidencia de una acción ya verificada como eficaz."))

    def _sellar_verificacion(self, anterior):
        """Verificar la eficacia ES el acto: lo registra quien lo ejecuta.

        Hasta el 2026-08-23 la acción de mejora —el documento donde de verdad
        vive la acción correctiva de ISO 9001 §10.2— no guardaba NINGÚN rastro de
        quién revisó su eficacia. En el recorrido de ese día se comprobó lo que
        eso significa: tras cerrarla la DPGC, el propio responsable (el auditado)
        editó la acción cerrada y `modified_by` pasó a ser él. Lo único que
        quedaba del verificador era el log de versiones, y un auditor externo
        mira el documento, no el log.

        `verificada_por` es read_only y lo pone el sistema al ENTRAR en cualquiera
        de las dos verificaciones —comparando con el estado anterior—, así que si
        la acción se reabre («Verificada no eficaz -> Reabrir») y se vuelve a
        verificar, queda quien verifica ESTA vez. Mismo patrón que
        `No Conformidad`, `Documento Controlado` y `Programa Auditoria`.
        """
        if self.estado not in VERIFICACIONES:
            # «Reabrir» devuelve la acción al ciclo de ejecución: la firma anterior
            # deja de describir lo que la acción es AHORA (la vuelta nueva tendrá la
            # suya). Se borra para que nadie lea «verificada por X» en una acción
            # que está sin verificar; el histórico queda en el log de versiones.
            if anterior and anterior.estado in VERIFICACIONES:
                self.verificada_por = None
            return

        if not anterior or anterior.estado != self.estado:
            self.verificada_por = frappe.session.user

    def _fijar_avance(self, anterior):
        """Avance implícito por estado + el 100 heredado que había que limpiar.

        `Ejecutada` fija 100. Al salir de ahí hacia un estado que NO es de
        cierre —«Verificar no eficaz» o «Reabrir», las dos únicas salidas— ese
        100 dejaba de ser cierto y nadie lo tocaba: en el recorrido del
        2026-08-23 la acción volvió a «En ejecucion» arrastrando avance 100, y
        el plan padre siguió anunciando 100 % de avance mientras su única acción
        se estaba rehaciendo por haber fallado la verificación.

        Al salir de un estado que fijaba el 100, el avance vuelve a 0: el trabajo
        hay que rehacerlo y el responsable declara de nuevo por dónde va. Un %
        manual distinto de 100 se respeta (es información suya, no un resto).
        """
        if self.estado in ESTADO_AVANCE:
            self.avance_pct = ESTADO_AVANCE[self.estado]
        elif (
            anterior
            and anterior.estado != self.estado
            and int(self.avance_pct or 0) >= 100
        ):
            self.avance_pct = 0

        self.avance_pct = max(0, min(100, int(self.avance_pct or 0)))

    def on_update(self):
        self._recalcular_plan()

    def on_trash(self):
        # on_trash corre ANTES del delete físico: hay que excluir esta acción del
        # recálculo, si no seguiría contando en el promedio del plan.
        self._recalcular_plan(excluir=self.name)

    def _recalcular_plan(self, excluir=None):
        """Propaga el avance/semáforo al plan padre. set_value directo dentro de
        recalcular_avance evita recursión (no re-guarda el plan entero)."""
        if self.plan_mejora and frappe.db.exists("Plan Mejora", self.plan_mejora):
            frappe.get_doc("Plan Mejora", self.plan_mejora).recalcular_avance(
                save=True, excluir_accion=excluir
            )
