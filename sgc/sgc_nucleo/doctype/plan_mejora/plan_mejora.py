# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M11 — Plan de Mejora: el contenedor de las acciones correctivas y de mejora.

ISO 9001:2015 §10.2 exige, ante una no conformidad, evaluar la necesidad de
acciones, implementarlas y **revisar la eficacia** de las tomadas. El plan es el
contenedor de esas acciones y de sus compromisos de fecha; su ciclo de vida lo
gobierna el Select `estado` (Borrador -> En ejecucion -> Cerrado, workflow
"Plan de Mejora SGC" de f4_workflow_mejora).

Las dos transiciones que este controlador vigila son las dos que el diagrama
marca como control (`autoaprobacion=0`): aprobar y cerrar. Ambas dejan firma
sellada por el sistema, y ambas comprueban que el plan tiene el contenido que
esa etapa exige — el workflow por sí solo solo mueve el Select.
"""

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import add_days, getdate, nowdate

from sgc.naming import codigo_anual

# Estado final de una acción que SÍ acredita mejora: ejecutada y verificada
# eficaz (ISO 9001 §10.2.1 d). "Ejecutada" todavía no lo está —le falta la
# verificación— y "Verificada no eficaz" es la declaración expresa de que no
# sirvió.
ACCION_CONCLUIDA_EFICAZ = "Verificada eficaz"


class PlanMejora(Document):
    def before_insert(self):
        # autoname es `field:codigo`: si no se indicó, se compone PM-{{anio}}-NNNN.
        # Hasta el 2026-08-23 no lo componía nadie salvo `capa.py` al crearlo, así
        # que crear uno por cualquier otra vía fallaba con «Código is required».
        if not self.codigo:
            self.codigo = codigo_anual(self.doctype, "PM")

    def validate(self):
        self._sellar_firmas()
        self._validar_puesta_en_ejecucion()
        self._validar_cierre()
        # Recalcula en memoria; el save del propio plan persiste los campos.
        self.recalcular_avance(save=False)

    # ------------------------------------------------------------------ firmas
    def _sellar_firmas(self):
        """Aprobar y cerrar el plan SON actos de firma: los registra quien los ejecuta.

        Comprobado en el recorrido del 2026-08-23: el plan no tenía dónde constar
        quién lo aprobó ni quién lo cerró. Se aprobaba y se cerraba y el documento
        solo guardaba `modified_by` —que lo pisa cualquier edición posterior—, así
        que la evidencia de la decisión de control se perdía. ISO 9001 §10.2.2
        pide conservar información documentada de la naturaleza de las acciones y
        de sus resultados; sin firma no hay tal cosa.

        Los cuatro campos son `read_only` en el .json Y en `f1_nucleo.py`: que el
        workflow prohíba la autoaprobación no sirve de nada si el REGISTRO de
        quién aprobó es tecleable. Mismo arreglo que
        `ProgramaAuditoria._sellar_aprobacion` y `Documento Controlado`.

        Se sella al ENTRAR en el estado —comparando con `get_doc_before_save()`—
        para que una reaprobación tras «Devolver a borrador» registre a quien
        aprueba esta vez, no al de la ronda anterior.

        `responsable` se queda fuera a propósito: es quien responde por ejecutar
        el plan, no quien lo aprueba, y se declara aparte.
        """
        anterior = self.get_doc_before_save()

        if self.estado == "En ejecucion" and (not anterior or anterior.estado != "En ejecucion"):
            self.aprobado_por = frappe.session.user
            self.fecha_aprobacion = nowdate()

        if self.estado == "Cerrado" and (not anterior or anterior.estado != "Cerrado"):
            self.cerrado_por = frappe.session.user
            self.fecha_cierre = nowdate()

    # ------------------------------------------------------------ validaciones
    def _validar_puesta_en_ejecucion(self):
        """Un plan que entra en ejecución tiene que tener algo que ejecutar y alguien que responda.

        Comprobado en el recorrido del 2026-08-23: la DPGC pulsó «Aprobar y
        ejecutar» sobre PM-2026-0001, que no tenía ni una sola `Accion Mejora` ni
        `responsable`, y el plan quedó «En ejecucion» con avance 0 % y semáforo
        Verde. Un plan vacío en verde es peor que no tener plan: el tablero lo
        cuenta como respuesta dada a la no conformidad que lo originó.

        ISO 9001 §10.2.1 b) exige evaluar la necesidad de acciones y §10.2.2
        conservar constancia de las tomadas. Sin acciones no hay ninguna.

        Se comprueba solo al ENTRAR en el estado: un plan que ya está en
        ejecución no se bloquea por editar cualquier otro campo.
        """
        if self.estado != "En ejecucion" or self.is_new():
            return
        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == "En ejecucion":
            return

        if not self.responsable:
            frappe.throw(
                _("Asigne un responsable del plan antes de ponerlo en ejecución."),
                title=_("Plan sin responsable"),
            )
        if not frappe.db.count("Accion Mejora", {"plan_mejora": self.name}):
            frappe.throw(
                _("El plan no tiene ninguna acción de mejora: no hay nada que ejecutar."),
                title=_("Plan vacío"),
            )

    def _validar_cierre(self):
        """Un plan se cierra cuando sus acciones se verificaron eficaces (ISO 9001 §10.2.1 d).

        Dos cierres en falso comprobados en el recorrido del 2026-08-23:

        1. PM-2026-0001 se cerró con sus dos acciones todavía en «Planificada»,
           avance 0 %. Nada se hizo y el plan figura cerrado.
        2. PM-2026-0004 se cerró cuando su única acción estaba «Verificada no
           eficaz» — es decir, revisada y declarada inútil — y el plan salió con
           avance 100 % y semáforo Verde, porque el 100 % se lo había fijado el
           paso previo «Ejecutada» y `_calcular_semaforo` pinta de Verde todo plan
           cerrado. El sistema daba por buena precisamente la acción que alguien
           acababa de declarar ineficaz.

        Por eso el criterio de cierre es «Verificada eficaz», no «Ejecutada»:
        §10.2.1 d) no pide ejecutar, pide revisar la eficacia de lo ejecutado. Una
        acción ineficaz obliga a reabrirla («Reabrir», en el workflow de Accion
        Mejora) o a plantear otra; lo que no puede es cerrarse el plan encima.

        Y se exige al menos una acción por el mismo motivo que en la puesta en
        ejecución: un plan sin acciones no acredita mejora ninguna.
        """
        if self.estado != "Cerrado" or self.is_new():
            return
        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == "Cerrado":
            return

        acciones = frappe.get_all(
            "Accion Mejora",
            filters={"plan_mejora": self.name},
            fields=["name", "estado"],
        )
        if not acciones:
            frappe.throw(
                _("No se puede cerrar un plan sin ninguna acción de mejora."),
                title=_("Plan vacío"),
            )

        pendientes = [a for a in acciones if a.estado != ACCION_CONCLUIDA_EFICAZ]
        if pendientes:
            frappe.throw(
                _("No se puede cerrar el plan: {0} acción(es) sin verificar como eficaces ({1}).").format(
                    len(pendientes),
                    ", ".join(f"{a.name} — {a.estado}" for a in pendientes[:5]),
                ),
                title=_("Acciones sin eficacia verificada"),
            )

    # ------------------------------------------------------------------ rollup
    def recalcular_avance(self, save=True, excluir_accion=None):
        """avance_pct = promedio del avance de sus acciones; fecha_compromiso = la
        más tardía; semaforo por vencimiento (RF-C06). Idempotente.

        Se llama desde el propio plan (validate) y desde Accion Mejora cuando una
        acción cambia. Con save=True persiste sin re-disparar validaciones (evita
        recursión plan<->acción). `excluir_accion` omite una acción del cálculo:
        necesario al borrar una acción, porque `on_trash` corre ANTES del delete
        físico y la acción todavía figuraría en el promedio."""
        filtros = {"plan_mejora": self.name}
        if excluir_accion:
            filtros["name"] = ["!=", excluir_accion]
        acciones = frappe.get_all(
            "Accion Mejora",
            filters=filtros,
            fields=["avance_pct", "fecha_compromiso", "estado"],
        )
        if acciones:
            avances = [int(a.avance_pct or 0) for a in acciones]
            self.avance_pct = round(sum(avances) / len(acciones))
            fechas = [getdate(a.fecha_compromiso) for a in acciones if a.fecha_compromiso]
            self.fecha_compromiso = max(fechas) if fechas else None
        else:
            self.avance_pct = 0
            self.fecha_compromiso = None
        self.semaforo = self._calcular_semaforo(acciones)

        if save and not self.is_new():
            frappe.db.set_value(
                "Plan Mejora", self.name,
                {
                    "avance_pct": self.avance_pct,
                    "fecha_compromiso": self.fecha_compromiso,
                    "semaforo": self.semaforo,
                },
                update_modified=False,
            )

    def _calcular_semaforo(self, acciones):
        """Rojo: alguna acción abierta ya vencida. Ambar: alguna abierta por vencer
        en <=15 días. Verde: al día o plan cerrado.

        El atajo «plan cerrado -> Verde» solo es honesto porque `_validar_cierre`
        garantiza que un plan cerrado tiene todas sus acciones verificadas
        eficaces. Antes de ese guard, cerrar era la forma de poner en verde un
        plan que no había ejecutado nada."""
        if self.estado == "Cerrado":
            return "Verde"
        hoy = getdate(nowdate())
        limite_ambar = getdate(add_days(hoy, 15))
        abiertas = [
            a for a in acciones
            if a.estado not in ("Ejecutada", "Verificada eficaz")
        ]
        for a in abiertas:
            if a.fecha_compromiso and getdate(a.fecha_compromiso) < hoy:
                return "Rojo"
        for a in abiertas:
            if a.fecha_compromiso and getdate(a.fecha_compromiso) <= limite_ambar:
                return "Ambar"
        return "Verde"
