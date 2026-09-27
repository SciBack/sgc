# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Qué exige cada metodología a cada causa para que el análisis diga algo (#34).
DATO_POR_METODOLOGIA = {
    "Cinco porqués": ("nivel", "el nivel en la cadena de porqués"),
    "Espina de pescado (Ishikawa)": ("categoria", "la categoría de la espina (personas, método…)"),
    "Pareto": ("frecuencia", "la frecuencia"),
}

# Orden del ciclo de vida (coincide con el Workflow "No Conformidad SGC").
# Se usa para exigir, de forma incremental, lo que cada etapa requiere (RF-B05).
ORDEN = {
    "Abierta": 0,
    "En analisis": 1,
    "En tratamiento": 2,
    "En verificacion": 3,
    "Cerrada eficaz": 4,
    "Cerrada no eficaz": 4,
}


class NoConformidad(Document):
    def validate(self):
        # Una NC mayor siempre exige análisis de causa raíz.
        if self.tipo == "No conformidad mayor":
            self.requiere_analisis_causa = 1

        if not self.fecha_deteccion:
            self.fecha_deteccion = nowdate()

        nivel = ORDEN.get(self.estado, 0)

        # A partir de "En analisis": debe haber un responsable asignado.
        if nivel >= 1 and not self.responsable:
            frappe.throw(_("Asigna un responsable antes de pasar la NC a análisis."))

        # A partir de "En tratamiento": si requiere análisis de causa, debe estar redactado.
        if nivel >= 2 and self.requiere_analisis_causa and not (self.analisis_causa or "").strip():
            frappe.throw(_("Esta NC requiere análisis de causa antes de pasar a tratamiento."))

        self._validar_analisis_estructurado(nivel)

        # A partir de "En verificacion": plazo comprometido + acción correctiva
        # (un plan de mejora vinculado o, al menos, una corrección inmediata registrada).
        if nivel >= 3:
            if not self.fecha_compromiso:
                frappe.throw(_("Define la fecha de compromiso (plazo) antes de enviar a verificación."))
            if not self.plan_mejora and not (self.correccion_inmediata or "").strip():
                frappe.throw(_("Vincula un plan de mejora o registra una corrección antes de verificar."))

        self._sellar_verificacion()

        # Al cerrar: evidencia de cierre. Quién verificó lo pone el propio acto,
        # ver `_sellar_verificacion`.
        if self.estado in ("Cerrada eficaz", "Cerrada no eficaz") and not self.evidencia_cierre:
            frappe.throw(_("Adjunta la evidencia de cierre para cerrar la NC."))

    def _validar_analisis_estructurado(self, nivel):
        """ISO 9001 §10.2.1 b: determinar las causas, con método, antes de tratar (#34).

        Un texto libre no distingue un análisis real de una frase escrita para
        pasar de estado. Por eso, cuando la NC requiere análisis, el paso a
        tratamiento exige además declarar la metodología, identificar al menos una
        causa y marcar al menos una como raíz; y cada causa trae el dato que su
        metodología necesita (nivel, categoría o frecuencia).

        Se comprueba **al pasar** a tratamiento, no en cada guardado: es el control
        del acto. Una NC anterior a #34 que ya estaba en tratamiento o más allá
        sigue guardando con su análisis en texto, sin migración; y una carga que
        aterriza ya en un estado avanzado (semilla, importación) no es un acto de
        nadie. Misma doctrina que `Accion Mejora._exigir_lo_de_cada_etapa`.
        """
        if not self.requiere_analisis_causa or nivel < 2:
            return
        anterior = self.get_doc_before_save()
        if not anterior or ORDEN.get(anterior.estado, 0) >= 2:
            return

        if not self.metodologia:
            frappe.throw(
                _("Declare la metodología del análisis de causas (cinco porqués, "
                  "Ishikawa, Pareto…) antes de pasar a tratamiento."),
                title=_("Análisis sin metodología"),
            )
        if not self.causas:
            frappe.throw(
                _("Registre al menos una causa identificada antes de pasar a tratamiento."),
                title=_("Análisis sin causas"),
            )
        if not any(c.es_causa_raiz for c in self.causas):
            frappe.throw(
                _("Marque al menos una causa como causa raíz: la acción correctiva tiene "
                  "que atacar la raíz, no el síntoma."),
                title=_("Sin causa raíz"),
            )
        dato = DATO_POR_METODOLOGIA.get(self.metodologia)
        if dato:
            campo, que = dato
            faltan = [c.idx for c in self.causas if not c.get(campo)]
            if faltan:
                frappe.throw(
                    _("Con «{0}», cada causa necesita {1}. Falta en las filas: {2}.").format(
                        self.metodologia, que, ", ".join(str(n) for n in faltan)),
                    title=_("Causas incompletas"),
                )

    def _sellar_verificacion(self):
        """Verificar la eficacia ES el acto: lo registra quien lo ejecuta.

        ISO 9001 §10.2.1 e) pide revisar la eficacia de la acción correctiva, y
        `verificada_por` es el registro de esa revisión. Era un Link que
        rellenaba a mano cualquiera con permiso de edición — empezando por el
        responsable que trató la NC, o sea el auditado. Comprobado en el
        recorrido del 2026-08-23: el responsable escribió ahí a un tercero, la
        DPGC cerró de verdad, y la NC quedó registrando como verificador a
        alguien que no la miró.

        Que el workflow impida la autoverificación (`allow_self_approval=0` en
        ambos cierres) no sirve de nada si el REGISTRO de esa firma es tecleable:
        un auditor externo mira este campo, no el log de transiciones.

        Se sella al ENTRAR en cualquiera de los dos cierres —comparando con el
        estado anterior— para que, si la NC se reabre y se vuelve a cerrar, quede
        quien verifica esta vez. Mismo patrón que `Documento Controlado` y
        `Programa Auditoria`.
        """
        cierres = ("Cerrada eficaz", "Cerrada no eficaz")
        if self.estado not in cierres:
            return

        anterior = self.get_doc_before_save()
        if not anterior or anterior.estado not in cierres:
            self.verificada_por = frappe.session.user
