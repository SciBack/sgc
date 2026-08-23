# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe import _
from frappe.model.document import Document


class Autoevaluacion(Document):
    def validate(self):
        self._validar_marco_es_de_acreditacion()
        self._validar_alcance_coherente()

    def _validar_marco_es_de_acreditacion(self):
        """Una autoevaluación acredita; no sirve para el permiso de operar.

        Sin esto se podía abrir una autoevaluación con el marco de
        LICENCIAMIENTO y el motor de acreditación la procesaba como si tal:
        comprobado en producción el 2026-08-23, calificando sus condiciones se
        obtenía «Acreditado 6 años» a partir de un marco que no acredita nada.
        El agravante está en las siglas: en la escala de licenciamiento «LP»
        significa literalmente *Cumple*, no *logrado plenamente*, y el motor
        solo ve la sigla.

        Son dos mundos que la norma mantiene separados a propósito. El propio
        Modelo de Acreditación Institucional del Coneau (2026, §4.2) explica
        que sus estándares se definieron revisando las condiciones básicas de
        Sunedu «para diferenciar los niveles de exigencia»: el licenciamiento
        es el piso obligatorio, la acreditación el reconocimiento voluntario.
        Cruzarlos produce un resultado que ninguna entidad ha otorgado.

        El licenciamiento tiene su propia puerta: `Informe Cumplimiento`.
        """
        if not self.marco_normativo:
            return
        marco = frappe.db.get_value(
            "Marco Normativo", self.marco_normativo, ["ente", "alcance"], as_dict=True
        ) or {}
        if marco.get("alcance") == "Licenciamiento" or marco.get("ente") == "SUNEDU":
            frappe.throw(
                _("El marco «{0}» es de licenciamiento (permiso para operar), no de "
                  "acreditación. El cumplimiento de las condiciones básicas se registra "
                  "en un Informe de Cumplimiento, no en una autoevaluación.").format(
                      self.marco_normativo),
                title=_("Marco de licenciamiento"),
            )

    def _validar_alcance_coherente(self):
        """Acreditar una carrera y acreditar la universidad no son lo mismo.

        La norma son dos modelos distintos, con distinto número de estándares
        (10 en programas, 9 institucional) y distinto umbral de excelencia (16
        puntos frente a 20). Antes esa diferencia solo vivía en el nombre del
        marco, así que cabía una autoevaluación de programa SIN programa —un
        expediente de carrera sin decir de qué carrera— y una institucional CON
        un programa colgado, que sobra y confunde a quien lea el informe.
        """
        if not self.marco_normativo:
            return
        alcance = frappe.db.get_value("Marco Normativo", self.marco_normativo, "alcance")
        if alcance == "Acreditación de programa" and not self.programa_sede:
            frappe.throw(
                _("Este marco acredita un programa de estudios: indica a qué "
                  "programa-sede corresponde la autoevaluación."),
                title=_("Falta el programa"),
            )
        if alcance == "Acreditación institucional" and self.programa_sede:
            frappe.throw(
                _("La acreditación institucional evalúa a la universidad entera: "
                  "no lleva un programa-sede asignado (indicado: {0}).").format(
                      self.programa_sede),
                title=_("Alcance institucional"),
            )

    def before_submit(self):
        """Congela el árbol del marco normativo justo antes del submit (Cerrada).

        Corre en el `_action == "submit"` de `run_before_save_methods` (ver
        `frappe/model/document.py`), es decir ANTES de que el docstatus quede
        persistido en 1 -- en ese instante el árbol vivo de Elemento Marco
        todavía es la fuente correcta a congelar. A partir de aquí
        `sgc.scoring` lee `marco_snapshot` en vez de consultar en vivo para
        esta autoevaluación, blindando el resultado contra ediciones
        posteriores del marco (reparenteos, correcciones de texto, etc.).
        """
        from sgc import scoring

        self.marco_snapshot = scoring.construir_snapshot(self.name)
        self._promover_vigencia()

    def _promover_vigencia(self):
        """Cerrar ES promover la vigencia: son el mismo acto, no dos pasos.

        Así lo define la documentación del producto —el paso 4 del manual se
        titula literalmente «Cerrar la autoevaluación: promover la vigencia
        oficial»— y así lo exige el modelo CONEAU, cuya sección 9.2 dice que «de
        acuerdo con los resultados de evaluación, se determina el periodo de
        vigencia» (Tabla 9): la vigencia no es una decisión aparte, es la
        consecuencia de los niveles confirmados.

        Estaban desacoplados, y eso abría dos huecos que se vieron en el
        recorrido de producción del 20-ago: se podía **cerrar sin vigencia**
        (quedaba vacía y nada avisaba), y `finalizar_vigencia` **escribía sobre
        el expediente ya cerrado** —inocuo hoy, porque deriva de niveles ya
        inmutables, pero un expediente cerrado no debe aceptar escrituras—.

        Al engancharlo aquí, cerrar sin los estándares confirmados falla: no hay
        vigencia determinable, así que no hay cierre. Corre ANTES del submit,
        con el docstatus todavía en 0, de modo que la escritura es legítima.
        """
        from sgc.confirmacion import calcular_vigencia_oficial

        resultado = calcular_vigencia_oficial(self.name)
        if not resultado.get("ok"):
            frappe.throw(
                frappe._(
                    "No se puede cerrar: faltan {0} estándares por confirmar. "
                    "La vigencia se determina a partir de los niveles confirmados "
                    "(Tabla 9 del modelo CONEAU), así que sin ellos no hay "
                    "resultado que registrar."
                ).format(resultado.get("faltan", "?")),
                title=frappe._("Autoevaluación incompleta"),
            )
        # Se asigna en memoria a propósito: el submit persiste este mismo doc.
        # Escribir aquí con db.set_value tocaría por debajo la fila que se está
        # guardando y el submit se enreda con su propio documento.
        self.resultado_vigencia = resultado["vigencia"]

    @frappe.whitelist()
    def datos_informe(self):
        """Contrato tipado del Informe de Autoevaluación (formato SINEACE).

        Devuelve exactamente `sgc.informe.consolidar(self.name)`: cabecera + estándares
        (nivel, semáforo, criterios, evidencias) + vigencia + matriz-resumen + anexo.

        Es el seam único de consumo del informe:
        - La plantilla Jinja del Print Format lo invoca con `doc.datos_informe()`.
        - Reservado como contrato MCP tipado (misma forma para la herramienta externa).

        Whitelisted para poder llamarse por API/plantilla; respeta permisos del doc.
        """
        from sgc.informe import consolidar

        return consolidar(self.name)

    @frappe.whitelist()
    def generar_pdf_informe(self, adjuntar=False):
        """Genera el PDF del informe (motor Chrome v16). Ver `sgc.informe.generar_pdf`.

        Con `adjuntar` truthy, lo guarda como File adjunto y devuelve {file_name, file_url}.
        """
        from sgc.informe import generar_pdf

        adjuntar = frappe.utils.cint(adjuntar)
        return generar_pdf(self.name, adjuntar=bool(adjuntar))
