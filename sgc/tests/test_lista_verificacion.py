# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Listas de verificación de auditoría (#32, ISO 19011 §6.3.4).

  Plantillas
    - una lista sin auditoría es plantilla y se queda en Borrador
    - usarla en una auditoría copia las preguntas y deja los resultados vacíos
  Validaciones
    - un punto sin pregunta se rechaza
    - completar exige puntos y que todos tengan resultado, diciendo cuántos faltan
    - quién la completó lo sella el sistema
  Hallazgos
    - uno por punto No conforme u Observación, ninguno por Conforme o No aplica
    - el tipo corresponde al resultado; la segunda pasada no duplica
  Auditoría cerrada
    - la lista no admite cambios, altas, borrado ni generar hallazgos

Todo se deshace al final de cada test (rollback de `IntegrationTestCase`).
"""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.sgc_auditoria.doctype.lista_verificacion.lista_verificacion import RESULTADO_A_TIPO
from sgc.tests import factories

DOCTYPE = "Lista Verificacion"
AUDITOR = "sgc-prueba-lv-auditor@example.com"


def _usuario(correo, *roles):
    if frappe.db.exists("User", correo):
        return
    u = frappe.get_doc({"doctype": "User", "email": correo, "first_name": correo.split("@")[0],
                        "send_welcome_email": 0})
    for rol in ("System Manager", *roles):
        u.append("roles", {"role": rol})
    u.insert(ignore_permissions=True)


PREGUNTAS = [
    "¿Las actas se firman dentro del plazo?",
    "¿El registro de notas coincide con el acta?",
    "¿Se archiva la constancia de entrega?",
    "¿Hay evidencia de revisión por el coordinador?",
]


class IntegrationTestListaVerificacion(IntegrationTestCase):
    def setUp(self):
        _usuario(AUDITOR, "Auditor Interno")
        self.proceso = factories.crear_proceso(prefijo="LV").name
        auditoria = frappe.get_doc({"doctype": "Auditoria", "titulo": "Auditoría de prueba LV",
                                    "proceso": self.proceso})
        auditoria.insert(ignore_permissions=True)
        self.auditoria = auditoria.name

    def tearDown(self):
        frappe.set_user("Administrator")

    def _lista(self, auditoria=None, preguntas=PREGUNTAS, **overrides):
        vals = {
            "doctype": DOCTYPE,
            "titulo": "Emisión de actas",
            "auditoria": auditoria,
            "items": [{"pregunta": p} for p in preguntas],
        }
        vals.update(overrides)
        return frappe.get_doc(vals).insert(ignore_permissions=True)

    def _resultados(self, lista, *resultados):
        for item, resultado in zip(lista.items, resultados, strict=False):
            item.resultado = resultado
        lista.save(ignore_permissions=True)
        return lista

    def _cerrar_auditoria(self):
        frappe.db.set_value("Auditoria", self.auditoria, "estado", "Cerrada", update_modified=False)

    # -- plantillas -----------------------------------------------------------
    def test_una_plantilla_se_queda_en_borrador(self):
        plantilla = self._lista()
        plantilla.estado = "En ejecucion"
        with self.assertRaises(frappe.ValidationError):
            plantilla.save(ignore_permissions=True)

    def test_usar_la_plantilla_copia_las_preguntas_sin_resultados(self):
        plantilla = self._lista(proceso=self.proceso)
        nombre = plantilla.usar_en_auditoria(self.auditoria)

        nueva = frappe.get_doc(DOCTYPE, nombre)
        self.assertEqual(nueva.auditoria, self.auditoria)
        self.assertEqual(nueva.plantilla_origen, plantilla.name)
        self.assertEqual(nueva.estado, "Borrador")
        self.assertEqual([i.pregunta for i in nueva.items], PREGUNTAS)
        self.assertTrue(all(not i.resultado and not i.hallazgo for i in nueva.items))

    def test_reutilizar_una_lista_aplicada_no_arrastra_lo_que_se_encontro(self):
        anterior = self._resultados(self._lista(self.auditoria), "Conforme", "No conforme",
                                    "Observacion", "No aplica")
        otra = frappe.get_doc({"doctype": "Auditoria", "titulo": "Auditoría del año siguiente"})
        otra.insert(ignore_permissions=True)

        nueva = frappe.get_doc(DOCTYPE, anterior.usar_en_auditoria(otra.name))
        self.assertTrue(all(not i.resultado for i in nueva.items))
        self.assertEqual(nueva.proceso, self.proceso)

    # -- validaciones -----------------------------------------------------------
    def test_un_punto_sin_pregunta_se_rechaza(self):
        with self.assertRaises(frappe.ValidationError):
            self._lista(preguntas=["¿Se cumple?", ""])

    def test_completar_con_puntos_sin_resultado_dice_cuantos_faltan(self):
        lista = self._resultados(self._lista(self.auditoria), "Conforme", "No conforme")
        lista.estado = "Completada"
        with self.assertRaises(frappe.ValidationError) as ctx:
            lista.save(ignore_permissions=True)
        self.assertIn("Faltan 2", str(ctx.exception))

    def test_una_lista_vacia_no_se_completa(self):
        lista = self._lista(self.auditoria, preguntas=[])
        lista.estado = "Completada"
        with self.assertRaises(frappe.ValidationError):
            lista.save(ignore_permissions=True)

    def test_completar_sella_quien_y_cuando(self):
        lista = self._resultados(self._lista(self.auditoria), "Conforme", "Conforme",
                                 "No aplica", "Conforme")
        lista.completada_por = "Guest"
        frappe.set_user(AUDITOR)
        self.addCleanup(frappe.set_user, "Administrator")
        lista.estado = "Completada"
        lista.save(ignore_permissions=True)
        self.assertEqual(lista.completada_por, AUDITOR)
        self.assertTrue(lista.fecha_completada)

    def test_el_auditor_por_defecto_es_quien_la_registra(self):
        self.assertEqual(self._lista(self.auditoria).auditor, "Administrator")

    # -- hallazgos ----------------------------------------------------------------
    def test_el_resultado_decide_el_tipo_del_hallazgo(self):
        self.assertEqual(RESULTADO_A_TIPO["No conforme"], "No conformidad menor")
        self.assertEqual(RESULTADO_A_TIPO["Observacion"], "Observacion")
        self.assertNotIn("Conforme", RESULTADO_A_TIPO)
        self.assertNotIn("No aplica", RESULTADO_A_TIPO)

    def test_genera_un_hallazgo_por_no_conforme_u_observacion(self):
        evidencia = factories.crear_evidencia(prefijo="LV").name
        lista = self._lista(self.auditoria)
        lista.items[1].evidencia = evidencia
        lista.items[1].evidencia_vista = "Acta 2026-II sin firma del docente."
        lista = self._resultados(lista, "Conforme", "No conforme", "Observacion", "No aplica")

        resultado = lista.generar_hallazgos()
        self.assertEqual(len(resultado["creados"]), 2)

        lista.reload()
        self.assertFalse(lista.items[0].hallazgo)
        self.assertFalse(lista.items[3].hallazgo)
        nc = frappe.get_doc("Hallazgo Auditoria", lista.items[1].hallazgo)
        obs = frappe.get_doc("Hallazgo Auditoria", lista.items[2].hallazgo)
        self.assertEqual(nc.tipo, "No conformidad menor")
        self.assertEqual(obs.tipo, "Observacion")
        self.assertEqual(nc.auditoria, self.auditoria)
        self.assertEqual(nc.proceso, self.proceso)
        self.assertIn("sin firma del docente", nc.descripcion)
        self.assertEqual([e.evidencia for e in nc.evidencia], [evidencia])

    def test_generar_dos_veces_no_duplica(self):
        lista = self._resultados(self._lista(self.auditoria), "No conforme", "Observacion",
                                 "Conforme", "Conforme")
        lista.generar_hallazgos()
        lista.reload()
        segunda = lista.generar_hallazgos()
        self.assertEqual(segunda["creados"], [])
        self.assertEqual(segunda["ya_existian"], 2)
        self.assertEqual(frappe.db.count("Hallazgo Auditoria", {"auditoria": self.auditoria}), 2)

    def test_una_plantilla_no_genera_hallazgos(self):
        plantilla = self._lista()
        with self.assertRaises(frappe.ValidationError):
            plantilla.generar_hallazgos()

    # -- auditoría cerrada ------------------------------------------------------------
    def test_con_la_auditoria_cerrada_no_se_modifica(self):
        lista = self._lista(self.auditoria)
        self._cerrar_auditoria()
        lista.items[0].resultado = "Conforme"
        with self.assertRaises(frappe.ValidationError):
            lista.save(ignore_permissions=True)

    def test_con_la_auditoria_cerrada_no_se_crea_ni_se_borra(self):
        lista = self._lista(self.auditoria)
        self._cerrar_auditoria()
        with self.assertRaises(frappe.ValidationError):
            self._lista(self.auditoria)
        with self.assertRaises(frappe.ValidationError):
            frappe.delete_doc(DOCTYPE, lista.name, ignore_permissions=True)

    def test_con_la_auditoria_cerrada_no_se_generan_hallazgos(self):
        lista = self._resultados(self._lista(self.auditoria), "No conforme", "Conforme",
                                 "Conforme", "Conforme")
        self._cerrar_auditoria()
        with self.assertRaises(frappe.ValidationError):
            lista.generar_hallazgos()
