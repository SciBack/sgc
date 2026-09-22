"""Correo (#41): qué se envía y qué se registra, sin bench ni base de datos.

Se fija la decisión pura. Que Frappe la aplique de verdad al enviar una regla lo
cubre `test_correo.py`.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def _cargar_correo():
    notification = types.ModuleType("frappe.email.doctype.notification.notification")
    notification.Notification = type("Notification", (), {})
    modulos = {
        "frappe": MagicMock(),
        "frappe.email": types.ModuleType("frappe.email"),
        "frappe.email.doctype": types.ModuleType("frappe.email.doctype"),
        "frappe.email.doctype.notification": types.ModuleType("frappe.email.doctype.notification"),
        "frappe.email.doctype.notification.notification": notification,
    }
    spec = importlib.util.spec_from_file_location("sgc_correo_puro", ROOT / "correo.py")
    modulo = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, modulos):
        spec.loader.exec_module(modulo)
    return modulo


correo = _cargar_correo()

DESTINOS = {"Para": ["ana@upeu.test", "beto@upeu.test"], "CC": ["carla@upeu.test"], "CCO": []}


class TestModoEnsayo(unittest.TestCase):
    def test_en_ensayo_no_sale_nada(self):
        a_enviar, _ = correo.decidir(DESTINOS, "Ensayo", [])
        self.assertEqual(a_enviar, {"Para": [], "CC": [], "CCO": []})

    def test_en_ensayo_se_registra_cada_destinatario_con_su_tipo(self):
        _, registros = correo.decidir(DESTINOS, "Ensayo", [])
        self.assertEqual(
            registros,
            [
                ("ana@upeu.test", "Para", correo.NO_ENVIADO),
                ("beto@upeu.test", "Para", correo.NO_ENVIADO),
                ("carla@upeu.test", "CC", correo.NO_ENVIADO),
            ],
        )

    def test_la_lista_blanca_no_abre_el_ensayo(self):
        """En ensayo no sale nada, aunque el destinatario esté en la lista blanca."""
        a_enviar, _ = correo.decidir(DESTINOS, "Ensayo", ["ana@upeu.test"])
        self.assertEqual(a_enviar["Para"], [])

    def test_un_modo_raro_o_ausente_es_ensayo(self):
        for modo in (None, "", "real", "Produccion"):
            a_enviar, _ = correo.decidir(DESTINOS, modo, [])
            self.assertEqual(a_enviar["Para"], [], modo)


class TestListaBlanca(unittest.TestCase):
    def test_dentro_de_la_lista_se_envia(self):
        a_enviar, registros = correo.decidir(DESTINOS, "Real", ["ana@upeu.test", "carla@upeu.test"])
        self.assertEqual(a_enviar["Para"], ["ana@upeu.test"])
        self.assertEqual(a_enviar["CC"], ["carla@upeu.test"])
        self.assertEqual(registros, [("beto@upeu.test", "Para", correo.OMITIDO)])

    def test_fuera_de_la_lista_queda_omitido_y_registrado(self):
        a_enviar, registros = correo.decidir(DESTINOS, "Real", ["otro@upeu.test"])
        self.assertEqual(sum(len(v) for v in a_enviar.values()), 0)
        self.assertEqual({r[2] for r in registros}, {correo.OMITIDO})
        self.assertEqual(len(registros), 3)

    def test_la_comparacion_no_distingue_mayusculas(self):
        a_enviar, _ = correo.decidir({"Para": ["Ana@UPeU.test"]}, "Real", ["ana@upeu.test"])
        self.assertEqual(a_enviar["Para"], ["Ana@UPeU.test"])

    def test_sin_lista_blanca_en_real_se_envia_a_todos(self):
        a_enviar, registros = correo.decidir(DESTINOS, "Real", [])
        self.assertEqual(a_enviar, DESTINOS)
        self.assertEqual(registros, [])


class TestNormalizarLista(unittest.TestCase):
    def test_acepta_lo_que_se_pega(self):
        texto = "Ana@upeu.test\n beto@upeu.test, carla@upeu.test;ana@upeu.test\n\n"
        self.assertEqual(
            correo.normalizar_lista(texto),
            ["ana@upeu.test", "beto@upeu.test", "carla@upeu.test"],
        )

    def test_vacia_o_nula_es_lista_vacia(self):
        self.assertEqual(correo.normalizar_lista(None), [])
        self.assertEqual(correo.normalizar_lista("  \n "), [])


if __name__ == "__main__":
    unittest.main()
