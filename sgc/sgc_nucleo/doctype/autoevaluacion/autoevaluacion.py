# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class Autoevaluacion(Document):
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
        from sgc.confirmacion import finalizar_vigencia

        resultado = finalizar_vigencia(self.name)
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
        # `finalizar_vigencia` persistió por db.set_value sobre la fila; el doc en
        # memoria es el que está a punto de guardarse, así que se alinea para que
        # el submit no lo pise con el valor viejo.
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
