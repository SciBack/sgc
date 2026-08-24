# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Riesgo — inventario GRC.

Fase 2 (2026-07-19, hallazgo): la cadena ISO 9001 §6.1/§10.2 (un riesgo que se
materializa debe alimentar el CAPA) estaba rota — `Riesgo` no tenía ningún camino
a `No Conformidad`. El esquema YA anticipaba esto (`No Conformidad.origen_tipo`
incluye "Riesgo materializado" desde el diseño original), pero nadie implementó
el método que lo dispara. Mismo patrón que
`sgc/sgc_auditoria/doctype/hallazgo_auditoria/hallazgo_auditoria.py::escalar_a_no_conformidad`
— reutiliza el origen polimórfico existente, no crea un mecanismo nuevo.

Recorrido del 2026-08-23 (flujo 13 en producción), tres cosas que no cuadraban:

  1. El método existía pero NO lo llamaba nadie: ni el workflow, ni un hook, ni
     el frontend. `sgc/bpmn.py` y el propio `f14_workflow_riesgos.py` afirmaban
     que «Materializar» disparaba el escalado; se comprobó en producción que
     «Materializar» solo cambiaba el estado y no creaba ninguna No Conformidad.
     Ahora el escalado ES un efecto de entrar en «Materializado» (`on_update`),
     que es lo que ambos ficheros ya declaraban.
  2. Un riesgo recorría entero Identificado → Evaluado → En tratamiento →
     Monitoreado → Cerrado sin una sola `Evaluacion Riesgo` ni un solo
     `Tratamiento Riesgo`. El inventario quedaba afirmando que un riesgo se
     analizó y se trató sin que existiera registro de ninguna de las dos cosas.
  3. Se cerraba un riesgo «Materializado» sin no conformidad y un riesgo
     «Monitoreado» con tratamientos a medias.
  4. `allow_self_approval=0` no protegía lo que se creía: Frappe compara al
     usuario con `doc.owner` (quien CREÓ la ficha), no con el `propietario` del
     riesgo. El dueño del riesgo confirmaba la materialización de su propio
     riesgo con solo no haber sido quien lo dio de alta.

Las validaciones son INCREMENTALES por estado (mismo patrón que M05
No Conformidad y M06 Programa Auditoria): cada estado exige, de forma
acumulativa, lo que esa etapa requiere.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Riesgo SGC" de
# `sgc/setup/f14_workflow_riesgos.py`). «Materializado» es una salida alterna de
# «Monitoreado», no un paso posterior: comparte nivel con él.
ORDEN = {
    "Identificado": 0,
    "Evaluado": 1,
    "En tratamiento": 2,
    "Monitoreado": 3,
    "Materializado": 3,
    "Cerrado": 4,
}

# Estados de `Tratamiento Riesgo` que significan "todavía no terminado".
# «Verificado» es el único cierre real de su workflow (f14): «Implementado» es
# el control puesto, pero sin que nadie haya comprobado que funciona.
TRATAMIENTO_ABIERTO = ("Planificado", "En ejecucion", "Implementado")

# Cierres de `No Conformidad` (workflow f2): la NC ya no está viva.
NC_CERRADA = ("Cerrada eficaz", "Cerrada no eficaz")

# Los dos estados que la DPGC concede como control (f14, `allow_self_approval=0`).
CONTROLES_DPGC = ("Cerrado", "Materializado")


class Riesgo(Document):
    def validate(self):
        self._validar_requisitos_por_estado()
        self._validar_control_independiente()
        self._validar_cierre()

    def on_update(self):
        self._escalar_al_materializarse()

    # ------------------------------------------------------- guards por estado
    def _validar_requisitos_por_estado(self):
        """Cada etapa exige el registro que la sostiene (acumulativo).

        Comprobado en el recorrido del 2026-08-23: un riesgo recién creado pasó
        «Evaluar», «Iniciar tratamiento» y «Monitorear» seguidos, sin ninguna
        `Evaluacion Riesgo` ni ningún `Tratamiento Riesgo`. El estado del riesgo
        es una AFIRMACIÓN — «esto ya se analizó», «esto ya se está tratando»— y
        se estaba pudiendo hacer sin nada detrás.

        - «Evaluado» exige al menos una `Evaluacion Riesgo`: ISO 31000 §6.4.3 y
          §6.4.4 sitúan ahí el análisis (probabilidad x consecuencia) y la
          valoración contra los criterios; ISO 9001:2015 §6.1.1 pide determinar
          los riesgos, no solo enunciarlos.
        - «En tratamiento» exige al menos un `Tratamiento Riesgo`: ISO 31000
          §6.5.1 (selección de la opción de tratamiento) e ISO 9001:2015 §6.1.2 a)
          (planificar las acciones para abordar el riesgo). Un riesgo "en
          tratamiento" sin tratamiento registrado no es trazable para nadie.
        """
        nivel = ORDEN.get(self.estado, 0)

        if nivel >= 1 and not self._tiene("Evaluacion Riesgo"):
            frappe.throw(
                _("Registre al menos una Evaluación de Riesgo (probabilidad e "
                  "impacto) antes de dar el riesgo por evaluado: es el análisis "
                  "y la valoración que exige ISO 31000 §6.4."),
                title=_("Riesgo sin evaluación"),
            )

        if nivel >= 2 and not self._tiene("Tratamiento Riesgo"):
            frappe.throw(
                _("Registre al menos un Tratamiento de Riesgo (la opción elegida "
                  "y su responsable) antes de pasar el riesgo a tratamiento."),
                title=_("Riesgo sin tratamiento"),
            )

    def _validar_control_independiente(self):
        """Los dos controles de la DPGC no los ejecuta el dueño del riesgo.

        El workflow ya los marca `allow_self_approval=0`, pero eso NO basta:
        `frappe.model.workflow.has_approval_access` compara al usuario con
        `doc.owner` —quien CREÓ la ficha— y el dueño del riesgo vive en el campo
        `propietario` (risk owner de ISO 31000 §5.4.4). Comprobado en el
        recorrido del 2026-08-23: un riesgo creado por el Dueño de Proceso y con
        `propietario` = una persona de la DPGC fue materializado por ESA MISMA
        persona, y el motor lo dejó pasar porque no era la creadora del
        documento.

        Confirmar que un riesgo se materializó, o darlo por cerrado, es el
        control que separa la gestión del riesgo de su verificación; quien
        responde por el riesgo no puede firmarlo. Mismo agujero y mismo arreglo
        que `TratamientoRiesgo._validar_verificador_independiente`.

        Sin excepción para `Administrator`, igual que en el tratamiento: en el
        SGC nadie opera este DocType como Administrator —todo va por rol— y la
        regla es del proceso, no del permiso. Que Frappe SÍ exima a Administrator
        en `has_approval_access` es otra razón por la que el workflow no bastaba.
        """
        if self.estado not in CONTROLES_DPGC or not self.propietario:
            return

        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == self.estado:
            return   # no es la transición, es un guardado cualquiera

        if frappe.session.user != self.propietario:
            return

        frappe.throw(
            _("Usted es el propietario de este riesgo: no puede ser quien confirme "
              "su cierre ni su materialización. Ese control lo ejerce otra persona "
              "de la DPGC."),
            title=_("Control sobre el propio riesgo"),
        )

    def _validar_cierre(self):
        """Cerrar un riesgo comprueba lo que el riesgo contiene.

        El cierre llega por dos caminos distintos y cada uno exige lo suyo, así
        que el guard mira DE DÓNDE viene (`get_doc_before_save`) y no solo dónde
        está:

        - Desde «Monitoreado»: ningún tratamiento puede quedar sin verificar.
          ISO 9001:2015 §6.1.2 b) pide evaluar la eficacia de las acciones
          tomadas frente a los riesgos; cerrar con tratamientos «Planificado»,
          «En ejecucion» o «Implementado» (puesto pero sin comprobar) declara
          eficaz lo que nadie miró. Comprobado el 2026-08-23: se cerró un riesgo
          cuyo tratamiento seguía sin existir siquiera.
        - Desde «Materializado»: el riesgo ya ocurrió, así que su no conformidad
          tiene que existir y estar cerrada. ISO 9001:2015 §10.2.1 obliga a
          reaccionar ante la no conformidad y a revisar la eficacia de la acción
          correctiva; cerrar el riesgo con la NC todavía viva archiva el riesgo
          y deja la reacción a medias. Comprobado el 2026-08-23: un riesgo
          materializado se cerró sin que existiera ninguna No Conformidad.
        """
        if self.estado != "Cerrado":
            return

        anterior = self.get_doc_before_save()
        venia_de = anterior.estado if anterior else None

        if venia_de == "Monitoreado":
            pendientes = frappe.get_all(
                "Tratamiento Riesgo",
                filters={"riesgo": self.name, "estado": ["in", TRATAMIENTO_ABIERTO]},
                pluck="name",
            )
            if pendientes:
                frappe.throw(
                    _("No se puede cerrar el riesgo: {0} tratamiento(s) sin verificar "
                      "({1}). Verifique su eficacia —o declárela no eficaz— antes de "
                      "cerrar.").format(len(pendientes), ", ".join(pendientes[:5])),
                    title=_("Cierre con tratamientos abiertos"),
                )

        if venia_de == "Materializado":
            nc = frappe.db.get_value(
                "No Conformidad",
                {"origen_doctype": "Riesgo", "origen_id": self.name},
                ["name", "estado"],
                as_dict=True,
            )
            if not nc:
                frappe.throw(
                    _("Este riesgo se materializó: antes de cerrarlo tiene que existir "
                      "su No Conformidad, que es donde ISO 9001 §10.2 sitúa la reacción "
                      "y la acción correctiva."),
                    title=_("Cierre sin no conformidad"),
                )
            if nc.estado not in NC_CERRADA:
                frappe.throw(
                    _("La no conformidad {0} de este riesgo sigue en «{1}». Ciérrela "
                      "antes de cerrar el riesgo: archivar el riesgo con su no "
                      "conformidad viva deja la acción correctiva a medias."
                      ).format(nc.name, nc.estado),
                    title=_("No conformidad todavía abierta"),
                )

    # ---------------------------------------------------------------- helpers
    def _tiene(self, doctype) -> bool:
        """¿Existe al menos un documento hijo de este tipo ligado al riesgo?"""
        if self.is_new():
            # Un riesgo recién creado no puede tener hijos: nadie pudo ligarlos
            # todavía. Solo aplica si nace en un estado avanzado, que el propio
            # workflow ya impide.
            return False
        return bool(frappe.db.exists(doctype, {"riesgo": self.name}))

    # ------------------------------------------------------------ escalamiento
    def _escalar_al_materializarse(self):
        """Entrar en «Materializado» crea la No Conformidad. Sin excepción.

        Comprobado en producción el 2026-08-23: `escalar_a_no_conformidad` no lo
        llamaba NADIE —ni el workflow, ni un hook, ni el frontend Vue, que no
        expone ningún botón—, así que la cadena §6.1 → §10.2 estaba escrita pero
        muerta. Y sin embargo dos sitios del código ya afirmaban que ocurría:
        `sgc/bpmn.py` (`SALTOS_ENTRE_PROCESOS`, que por eso dibuja el mensaje
        saliendo de la tarea «Materializar») y el docstring de
        `sgc/setup/f14_workflow_riesgos.py` («materializar dispara potencialmente
        una NC»). La declaración era correcta; lo que faltaba era el cable.

        Va en `on_update` y no en `validate` porque crea OTRO documento: si la
        transición se revierte, no debe quedar una NC huérfana. Es idempotente
        (el método busca la NC por origen), así que reguardar un riesgo ya
        materializado no duplica nada.
        """
        if self.estado != "Materializado":
            return

        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == "Materializado":
            return   # ya estaba materializado: esto es un guardado cualquiera

        self.escalar_a_no_conformidad()

    @frappe.whitelist()
    def escalar_a_no_conformidad(self):
        """Escala este riesgo (ya materializado) a una `No Conformidad`.

        Solo tiene sentido si `estado == "Materializado"` — un riesgo que no se
        materializó no es una no conformidad, es gestión preventiva normal.
        Idempotente: si ya hay una NC ligada (buscada por origen), devuelve esa.
        """
        if self.estado != "Materializado":
            frappe.throw(
                _("Solo un riesgo en estado «Materializado» puede escalar a una "
                  "No Conformidad. Estado actual: «{0}».").format(self.estado or _("(sin estado)"))
            )

        existente = frappe.db.get_value(
            "No Conformidad",
            {"origen_doctype": "Riesgo", "origen_id": self.name},
            "name",
        )
        if existente:
            return existente

        nc = frappe.get_doc({
            "doctype": "No Conformidad",
            "titulo": _("NC desde riesgo materializado {0}").format(self.name),
            "origen_doctype": "Riesgo",
            "origen_id": self.name,
            "origen_tipo": "Riesgo materializado",
            "tipo": "No conformidad mayor",
            "descripcion": self.descripcion or "",
            "unidad_organica": self.unidad_organica,
            "proceso": self.proceso,
            "criterio": self.elemento_marco,
            "estado": "Abierta",
            "requiere_analisis_causa": 1,
            "fecha_deteccion": nowdate(),
        }).insert(ignore_permissions=True)

        return nc.name
