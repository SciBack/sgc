# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""M06 / rama 4 — Revisión por la Dirección (ISO 9001:2015 e ISO 21001 §9.3).

La revisión por la dirección consolida las ENTRADAS del §9.3.2 (estado de
acciones previas, cambios de contexto, desempeño y eficacia del SGC, suficiencia
de recursos, eficacia frente a riesgos, oportunidades de mejora) y produce las
SALIDAS del §9.3.3 (decisiones y acciones sobre: oportunidades de mejora,
cambios en el SGC y necesidades de recursos).

`name` lo autogenera Frappe (autoname `format:RPD-{YYYY}-{##}`); el campo `codigo`
(reqd+unique) se rellena con el `name` si el usuario no lo indicó, para tener un
código legible sin duplicar la lógica de correlativo.

El ciclo de vida (Select `estado`: Planificada / Realizada / Cerrada) lo gobierna
el Workflow "Revision Direccion SGC" (sgc/setup/f10_workflow_revision.py, preside
la DPGC salvo el CIERRE, que ejecuta el Rectorado); este controlador solo aplica,
de forma incremental, lo que cada etapa exige — mismo enfoque que
`no_conformidad.py`.
"""
import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import nowdate

# Orden del ciclo de vida (coincide con el Workflow "Revision Direccion SGC").
# Sirve para exigir, de forma incremental, lo que cada etapa requiere.
ORDEN = {
    "Planificada": 0,
    "Realizada": 1,
    "Cerrada": 2,
}

# Entradas que ISO 9001:2015 §9.3.2 obliga a CONSIDERAR en toda revisión. Son
# exactamente los valores del Select `tipo_entrada` de Entrada Revision, y
# están en el mismo orden que los incisos a)-f) de la norma.
ENTRADAS_REQUERIDAS = (
    "Estado de acciones de revisiones previas",   # §9.3.2 a)
    "Cambios en cuestiones externas/internas",    # §9.3.2 b)
    "Desempeno y eficacia del SGC",               # §9.3.2 c)
    "Suficiencia de recursos",                    # §9.3.2 d)
    "Eficacia de acciones frente a riesgos",      # §9.3.2 e)
    "Oportunidades de mejora",                    # §9.3.2 f)
)

# Salidas/decisiones que ISO 9001:2015 §9.3.3 exige que produzca la revisión.
# Son exactamente los valores del Select `tipo_salida` de Salida Revision.
SALIDAS_REQUERIDAS = (
    "Oportunidad de mejora",
    "Cambio en el SGC",
    "Necesidad de recursos",
)

# Consolidación §9.3.2 -> §9.3.3: qué tipos de ENTRADA alimentan cada tipo de
# SALIDA obligatoria (valores reales de los Select `tipo_entrada`/`tipo_salida`).
CONSOLIDACION = {
    "Oportunidad de mejora": ["Oportunidades de mejora"],
    "Cambio en el SGC": [
        "Cambios en cuestiones externas/internas",
        "Desempeno y eficacia del SGC",
        "Eficacia de acciones frente a riesgos",
    ],
    "Necesidad de recursos": ["Suficiencia de recursos"],
}


class RevisionDireccion(Document):
    def validate(self):
        # `codigo` es reqd+unique; el `name` se autogenera (RPD-{YYYY}-{##}).
        # Si no se indicó código, se reutiliza el name como código legible.
        if not self.codigo:
            self.codigo = self.name

        # Primero el candado: una revisión cerrada no se toca sin reabrirla.
        self._bloquear_si_cerrada()
        self._sellar_cierre()

        nivel = ORDEN.get(self.estado, 0)

        # A partir de "Realizada": la revisión ya ocurrió -> fecha + entradas (§9.3.2).
        if nivel >= 1:
            if not self.fecha:
                self.fecha = nowdate()
            self._validar_entradas()

        # Al "Cerrar": deben existir las salidas/decisiones (§9.3.3) y el acta.
        if nivel >= 2:
            self._validar_salidas()
            if not self.pdf:
                frappe.throw(
                    _("Adjunta el acta/informe (PDF) para cerrar la revisión por la dirección.")
                )

    # ------------------------------------------------------------ cierre formal
    def _bloquear_si_cerrada(self):
        """Una revisión cerrada por la alta dirección no se edita: se reabre.

        El workflow lleva `allow_edit: DPGC` también en «Cerrada», y ese
        `allow_edit` ni siquiera se comprueba al guardar: comprobado en el
        recorrido del 2026-08-23, después de que el Rectorado cerrara
        RPD-2026-01 la DPGC sustituyó el acta adjunta, reescribió una de las
        decisiones del §9.3.3 y le añadió una entrada nueva — todo sin salir de
        «Cerrada» y sin pasar por «Reabrir revision». El cierre de la alta
        dirección quedaba ejercido sobre un contenido que después cambiaba solo.

        Eso vacía justo lo que §9.3.3 pide conservar: información documentada
        como evidencia de los resultados de la revisión. Evidencia reescribible
        en silencio no es evidencia.

        El candado deja pasar exactamente el save de la transición «Reabrir
        revision» (Cerrada -> Realizada), que es la vía que el diagrama dibuja
        para volver a tocarla: reabrir deja rastro en el workflow y obliga a que
        el Rectorado vuelva a cerrar lo que ahora dice el documento.
        """
        anterior = self.get_doc_before_save()
        if anterior and anterior.estado == "Cerrada" and self.estado == "Cerrada":
            frappe.throw(
                _("Esta revisión ya fue cerrada por la alta dirección y no puede "
                  "modificarse. Para corregirla, reábrela («Reabrir revision») y "
                  "vuelve a someterla al cierre del Rectorado."),
                title=_("Revisión cerrada"),
            )

    def _sellar_cierre(self):
        """Cerrar ES firmar: lo registra quien ejecuta la transición.

        El cierre es el acto formal de la alta dirección (ISO 9001:2015 §5.1.1:
        la responsabilidad sobre la eficacia del SGC no se delega en el área que
        lo administra), y por eso el workflow se lo reserva al Rectorado. Pero
        del documento no se podía deducir QUÉ persona lo ejerció: no había
        ningún campo que lo dijera — comprobado en el recorrido del 2026-08-23,
        tras el cierre solo quedaba `modified_by`, que la siguiente edición
        —o la reapertura— pisa.

        Mismo patrón que `Programa Auditoria._sellar_aprobacion`: se sella al
        ENTRAR en «Cerrada» comparando con el estado anterior, así un segundo
        cierre tras una reapertura registra a quien cierra esta vez. Y al salir
        de «Cerrada» se borra, para que una revisión reabierta no siga
        exhibiendo la firma de un cierre que ya no está vigente.

        Los campos son `read_only` en el DocType: nadie los teclea.
        """
        anterior = self.get_doc_before_save()
        entra_en_cerrada = self.estado == "Cerrada" and (not anterior or anterior.estado != "Cerrada")
        sale_de_cerrada = self.estado != "Cerrada" and anterior and anterior.estado == "Cerrada"

        if entra_en_cerrada:
            self.cerrada_por = frappe.session.user
            self.fecha_cierre = nowdate()
        elif sale_de_cerrada:
            self.cerrada_por = None
            self.fecha_cierre = None

    # ---------------------------------------------------------------- helpers
    def _validar_entradas(self):
        """§9.3.2 — las seis entradas de la norma, y ninguna en blanco.

        §9.3.2 no es una lista de la que se elige: enumera lo que la revisión
        «debe incluir» y sus seis incisos a)-f) son acumulativos. El sistema
        pedía UNA entrada cualquiera: comprobado en el recorrido del
        2026-08-23, RPD-2026-01 pasó a «Realizada» declarando solo
        «Oportunidades de mejora», sin que nadie hubiera mirado el estado de las
        acciones previas, el desempeño del SGC, los recursos ni la eficacia
        frente a los riesgos. Y RPD-2026-02 pasó con una fila creada vacía: el
        Select `tipo_entrada` no tiene opción en blanco, así que Frappe le pone
        la primera opción y pulsar «añadir fila» bastaba para dar por
        considerado el inciso a).

        Una entrada sin resumen ni fuente no evidencia nada, así que cada fila
        tiene que decir qué se consideró (`resumen`) o apuntar a la evidencia
        real (`fuente_id`: informe de auditoría, resultado de instrumento, valor
        de indicador, evaluación de riesgo…).

        Que no haya nada que reportar en un inciso NO lo exime: la primera
        revisión del SGC no tiene acciones previas, y eso se registra
        escribiéndolo («primera revisión: sin acciones previas»), que es
        precisamente considerarlo.
        """
        if not self.entradas:
            frappe.throw(
                _("Registra las entradas del §9.3.2 antes de marcar la revisión "
                  "como realizada.")
            )

        for fila in self.entradas:
            if not fila.tipo_entrada:
                frappe.throw(_("Cada entrada de la revisión debe indicar su tipo (§9.3.2)."))
            if not (fila.resumen or "").strip() and not fila.fuente_id:
                frappe.throw(
                    _("La entrada «{0}» está vacía: escribe el resumen de lo que se "
                      "consideró o enlaza la fuente que lo evidencia (§9.3.2).").format(
                          fila.tipo_entrada),
                    title=_("Entrada sin contenido"),
                )

        tipos_presentes = {(f.tipo_entrada or "").strip() for f in self.entradas}
        faltantes = [t for t in ENTRADAS_REQUERIDAS if t not in tipos_presentes]
        if faltantes:
            frappe.throw(
                _("La revisión no puede darse por realizada: el §9.3.2 obliga a "
                  "considerar todas estas entradas y faltan {0}: {1}. Si en alguna "
                  "no hay nada que reportar, regístralo diciéndolo.").format(
                      len(faltantes), ", ".join(faltantes)),
                title=_("Entradas del §9.3.2 incompletas"),
            )

    def _validar_salidas(self):
        """§9.3.3 — deben estar las 3 salidas obligatorias, con descripción y responsable."""
        if not self.salidas:
            frappe.throw(
                _("Registra las salidas/decisiones (§9.3.3) antes de cerrar la revisión.")
            )

        tipos_presentes = {(f.tipo_salida or "").strip() for f in self.salidas}
        faltantes = [t for t in SALIDAS_REQUERIDAS if t not in tipos_presentes]
        if faltantes:
            frappe.throw(
                _("La revisión no puede cerrarse: faltan las salidas obligatorias "
                  "(§9.3.3): {0}.").format(", ".join(faltantes))
            )

        for fila in self.salidas:
            if not (fila.descripcion or "").strip():
                frappe.throw(
                    _("Cada salida de la revisión debe describir la decisión o acción (§9.3.3).")
                )
            if not fila.responsable:
                frappe.throw(_("Cada salida (§9.3.3) debe tener un responsable asignado."))

    # ------------------------------------------------------------ consolidación
    @frappe.whitelist()
    def consolidar_salidas(self):
        """Genera el esqueleto de las salidas obligatorias (§9.3.3) que aún falten.

        Por cada tipo de salida requerido que no exista todavía, agrega una fila
        de Salida Revision con una descripción sembrada a partir de los resúmenes
        de las entradas (§9.3.2) que la alimentan (ver `CONSOLIDACION`). El
        responsable y la fecha de compromiso los completa luego la dirección.

        Idempotente: no duplica salidas de un tipo ya presente. Devuelve el número
        de salidas creadas.

        Escribe con los permisos de quien llama, no por encima de ellos. Antes
        guardaba con `ignore_permissions=True`, y como `run_doc_method` solo
        exige permiso de LECTURA para invocar un método whitelisted, cualquier
        rol de solo lectura podía redactar las decisiones del §9.3.3: comprobado
        en el recorrido del 2026-08-23, `prueba-auditor@sgc.local` (Auditor
        Interno, `write: 0`, y encima parte auditada del ciclo) sembró las tres
        salidas de RPD-2026-01 y quedó como `modified_by` de la revisión por la
        dirección. Un `save()` normal con `check_permission("write")` delante
        deja el método donde debe: una comodidad para quien ya podía editar.
        """
        self.check_permission("write")

        tipos_presentes = {(f.tipo_salida or "").strip() for f in self.salidas}
        creadas = 0

        for tipo_salida in SALIDAS_REQUERIDAS:
            if tipo_salida in tipos_presentes:
                continue

            resumenes = [
                (e.resumen or "").strip()
                for e in self.entradas
                if e.tipo_entrada in CONSOLIDACION.get(tipo_salida, []) and (e.resumen or "").strip()
            ]
            descripcion = (
                "\n".join(f"- {r}" for r in resumenes)
                if resumenes
                else _("(Pendiente de decidir por la dirección)")
            )

            self.append("salidas", {
                "tipo_salida": tipo_salida,
                "descripcion": descripcion,
            })
            creadas += 1

        if creadas:
            self.save()

        return creadas
