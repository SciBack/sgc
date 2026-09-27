# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Salida no conforme — ISO 9001:2015 §8.7 (#33).

Una salida no conforme es el producto o servicio concreto que se entregó mal: un
acta con notas mal cargadas, un certificado con un error, una constancia fuera
de plazo. **No es una `No Conformidad`**: aquella documenta que el sistema de
gestión falló en un requisito; esta, que una entrega salió mal. Un incidente
aislado se queda aquí; si revela un fallo del sistema, se escala
(`escalar_a_no_conformidad`) y las dos quedan enlazadas en ambos sentidos.

§8.7.2 pide conservar cuatro cosas, y cada una tiene su campo:

  a) la no conformidad          -> `descripcion`, `requisito_incumplido`
  b) las acciones tomadas       -> `acciones_tomadas`
  c) las concesiones obtenidas  -> `decision` + `justificacion_decision`
  d) la autoridad que decide    -> `autorizado_por`, que SELLA el sistema

El ciclo lo gobierna el Select `estado` (Detectada -> En tratamiento -> Tratada
-> Verificada -> Cerrada), con la vuelta «Devolver a tratamiento» que devuelve
a tratamiento lo que la verificación no da por bueno.

Reglas que sostiene este controlador, con la doctrina del resto del producto
(ver `Tratamiento Riesgo` y `No Conformidad`):

1. Cada etapa exige, de forma acumulativa, lo que esa etapa necesita.
2. Quién decidió y quién verificó lo sella el sistema al ENTRAR en el estado;
   no se teclea (un auditor mira el campo, no el log de transiciones).
3. Segregación de funciones en el controlador, porque `allow_self_approval=0`
   del workflow solo compara con `doc.owner`: una concesión no la autoriza
   quien detectó ni quien registró la salida, y el resultado no lo verifica
   quien trató ni quien decidió.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import cint, nowdate

DOCTYPE = "Salida No Conforme"

CONCESION = "Autorizar bajo concesion"

# Orden del ciclo de vida (coincide con el Workflow "Salida No Conforme SGC").
ORDEN = {
    "Detectada": 0,
    "En tratamiento": 1,
    "Tratada": 2,
    "Verificada": 3,
    "Cerrada": 4,
}

# Opción de `No Conformidad.origen_tipo` para lo que llega desde aquí.
ORIGEN_NC = "Salida no conforme"


class SalidaNoConforme(Document):
    def validate(self):
        self._completar_deteccion()
        self._validar_cantidad()
        self._validar_independencia()
        self._sellar_tratamiento()
        self._sellar_verificacion()
        self._validar_requisitos_por_estado()

    # ---------------------------------------------------------------- helpers
    def _estado_anterior(self):
        anterior = self.get_doc_before_save()
        return anterior.estado if anterior else None

    def _entra_en(self, estado):
        """True solo en el guardado que MUEVE el documento a `estado`."""
        return self.estado == estado and self._estado_anterior() != estado

    def _se_devuelve(self):
        """True en la vuelta «Devolver a tratamiento»: Tratada -> En tratamiento.

        Es tan acto de verificación como el que va a «Verificada»: alguien miró
        el tratamiento y concluyó que no basta.
        """
        return self.estado == "En tratamiento" and self._estado_anterior() == "Tratada"

    def _es_concesion(self):
        return self.decision == CONCESION

    # ------------------------------------------------------------ validaciones
    def _completar_deteccion(self):
        if not self.fecha_deteccion:
            self.fecha_deteccion = nowdate()
        if not self.detectado_por and self.is_new():
            self.detectado_por = frappe.session.user

    def _validar_cantidad(self):
        if self.cantidad_afectada is not None and cint(self.cantidad_afectada) < 0:
            frappe.throw(_("La cantidad afectada no puede ser negativa."))

    def _validar_independencia(self):
        """Las dos separaciones de funciones que el workflow solo no garantiza.

        **Concesión.** Aceptar una salida que no cumple es la decisión más
        delicada de §8.7: si la toma quien la detectó o la registró, nadie
        independiente la ha mirado. Se compara con `owner` (quien registró) y
        con `detectado_por`, porque pueden ser personas distintas y cualquiera
        de las dos tiene interés en cerrar el asunto.

        **Verificación.** Quien trató la salida o decidió qué hacer con ella no
        comprueba su propio resultado. Se comparan `responsable` y
        `autorizado_por`: el primero es tecleable hasta el final y el segundo lo
        selló el sistema, así que cambiar el responsable en el último momento no
        esquiva la regla.

        Sin excepción para Administrator, como en `Tratamiento Riesgo`: la regla
        es del proceso, no del permiso.
        """
        usuario = frappe.session.user

        if self._entra_en("Tratada") and self._es_concesion():
            if usuario in (self.owner, self.detectado_por):
                frappe.throw(
                    _("No puede autorizar bajo concesión una salida no conforme que "
                      "usted mismo detectó o registró. La concesión la decide otra "
                      "persona con autoridad sobre el proceso."),
                    title=_("Concesión no independiente"),
                )

        if self._entra_en("Verificada") or self._se_devuelve():
            if usuario in (self.responsable, self.autorizado_por):
                frappe.throw(
                    _("No puede verificar el tratamiento de una salida no conforme "
                      "que usted mismo trató o decidió."),
                    title=_("Verificación no independiente"),
                )

    def _validar_requisitos_por_estado(self):
        nivel = ORDEN.get(self.estado, 0)

        if nivel >= 1 and not self.responsable:
            frappe.throw(_("Asigne un responsable del tratamiento antes de iniciarlo."))

        if nivel >= 2:
            if not self.decision:
                frappe.throw(
                    _("Registre la decisión sobre la salida no conforme: corregir, "
                      "autorizar bajo concesión, suspender la entrega o retirar lo "
                      "entregado."),
                    title=_("Sin decisión"),
                )
            if not (self.acciones_tomadas or "").strip():
                frappe.throw(_("Describa las acciones tomadas antes de darla por tratada."))
            if self._es_concesion():
                if not (self.justificacion_decision or "").strip():
                    frappe.throw(
                        _("Una concesión exige justificar por qué se acepta la salida "
                          "tal como está."),
                        title=_("Concesión sin justificar"),
                    )
                if not self.autorizado_por:
                    frappe.throw(
                        _("Una concesión exige constancia de quién la autorizó."),
                        title=_("Concesión sin autorización"),
                    )

        if nivel >= 3:
            if not cint(self.verificacion_conformidad):
                frappe.throw(
                    _("Marque «Resultado comprobado»: verificar es comprobar el "
                      "resultado del tratamiento."),
                    title=_("Verificación sin constancia"),
                )
            if not self.evidencia_tratamiento:
                frappe.throw(
                    _("Vincule la evidencia del tratamiento antes de verificarlo."),
                    title=_("Sin evidencia"),
                )

        if self._se_devuelve() and not (self.observaciones_verificacion or "").strip():
            frappe.throw(
                _("Explique en las observaciones por qué el tratamiento no se da por "
                  "bueno antes de devolverlo."),
                title=_("Devolución sin motivo"),
            )

    # ------------------------------------------------------------------ sellos
    def _sellar_tratamiento(self):
        """Pasar a «Tratada» ES la decisión: la firma quien la toma (§8.7.2 d).

        Se sella al ENTRAR, para que tras una devolución quede quien decide esta
        vez. Al devolverse, el sello deja de ser cierto y se limpia, junto con la
        comprobación, que ya no vale.
        """
        if self._entra_en("Tratada"):
            self.autorizado_por = frappe.session.user
            self.fecha_tratamiento = nowdate()

        if self._se_devuelve():
            self.autorizado_por = None
            self.fecha_tratamiento = None
            self.verificacion_conformidad = 0

    def _sellar_verificacion(self):
        """Verificar ES el acto: lo firma quien lo ejecuta, también si es negativo."""
        if self._entra_en("Verificada") or self._se_devuelve():
            self.verificado_por = frappe.session.user
            self.fecha_verificacion = nowdate()

    # ------------------------------------------------------------ escalamiento
    @frappe.whitelist()
    def escalar_a_no_conformidad(self, tipo="No conformidad menor"):
        """Escala esta salida a una `No Conformidad` del sistema.

        Se escala cuando la salida no es un caso aislado: revela que el sistema
        falla (el mismo error se repite, el control no existía…). Queda la
        trazabilidad en ambos sentidos: aquí `no_conformidad`, y allí
        `origen_doctype` + `origen_id`.

        Respeta permisos, a diferencia de otros escalados del producto: crear una
        NC es una decisión con consecuencias y la toma quien tiene permiso para
        crearla. Idempotente: si ya hay NC, devuelve esa.
        """
        if self.no_conformidad:
            return self.no_conformidad

        existente = frappe.db.get_value(
            "No Conformidad", {"origen_doctype": DOCTYPE, "origen_id": self.name}, "name"
        )
        if existente:
            self.db_set("no_conformidad", existente)
            return existente

        if tipo not in ("No conformidad mayor", "No conformidad menor"):
            frappe.throw(_("Una salida no conforme escala a una no conformidad mayor o menor."))

        self.check_permission("write")

        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": _("NC desde salida no conforme {0}").format(self.name),
            "origen_doctype": DOCTYPE,
            "origen_id": self.name,
            "origen_tipo": ORIGEN_NC,
            "tipo": tipo,
            "descripcion": self.descripcion or "",
            "requisito_incumplido": self.requisito_incumplido,
            "unidad_organica": self.unidad_organica,
            "proceso": self.proceso,
            "programa_sede": self.programa_sede,
            "estado": "Abierta",
            "requiere_analisis_causa": 1,
            "fecha_deteccion": nowdate(),
        }).insert()

        self.db_set("no_conformidad", nc.name)
        return nc.name
