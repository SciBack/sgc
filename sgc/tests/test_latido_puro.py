"""Latido del scheduler (#42): el cálculo del desfase, sin bench ni base de datos.

Lo que se fija aquí es la decisión —¿hay que avisar?— con el estado ya leído.
Que el estado se lea bien de la instancia lo cubre `test_latido.py`.
"""
import importlib.util
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

ROOT = Path(__file__).resolve().parents[1]


def _cargar_latido():
    spec = importlib.util.spec_from_file_location("sgc_latido_puro", ROOT / "latido.py")
    modulo = importlib.util.module_from_spec(spec)
    with patch.dict(sys.modules, {"frappe": MagicMock()}):
        spec.loader.exec_module(modulo)
    return modulo


latido = _cargar_latido()

AHORA = datetime(2026, 9, 22, 12, 0, 0)
ALTA = AHORA - timedelta(days=30)


def tarea(metodo="sgc.tasks.a", horas=None, frecuencia="Daily", detenida=0, alta=ALTA, estado="Complete"):
    return {
        "metodo": metodo,
        "frecuencia": frecuencia,
        "detenida": detenida,
        "alta": alta,
        "ultima_ok": AHORA - timedelta(hours=horas) if horas is not None else None,
        "ultimo_estado": estado,
    }


class TestDesfase(unittest.TestCase):
    def test_marca_de_ayer_no_avisa(self):
        r = latido.evaluar([tarea(horas=20), tarea("sgc.tasks.b", horas=21)], AHORA, 48)
        self.assertFalse(r["alerta"])

    def test_marca_de_hace_tres_dias_avisa(self):
        r = latido.evaluar([tarea(horas=72), tarea("sgc.tasks.b", horas=73)], AHORA, 48)
        self.assertTrue(r["alerta"])
        self.assertEqual(r["horas_desde_ultima"], 72.0)

    def test_el_umbral_se_respeta_en_el_borde(self):
        """Exactamente en el umbral todavía no: se avisa al pasarlo."""
        self.assertFalse(latido.evaluar([tarea(horas=48)], AHORA, 48)["alerta"])
        self.assertTrue(latido.evaluar([tarea(horas=49)], AHORA, 48)["alerta"])

    def test_el_umbral_es_el_que_se_pasa(self):
        self.assertFalse(latido.evaluar([tarea(horas=60)], AHORA, 72)["alerta"])
        self.assertTrue(latido.evaluar([tarea(horas=60)], AHORA, 24)["alerta"])


class TestCasosQueLaMarcaMasRecienteTaparia(unittest.TestCase):
    def test_una_tarea_que_falla_no_la_tapa_otra_que_corre(self):
        """El fallo silencioso de verdad: el scheduler vive y una tarea muere a diario."""
        r = latido.evaluar(
            [tarea("sgc.tasks.sana", horas=5), tarea("sgc.tasks.rota", horas=120, estado="Failed")],
            AHORA,
            48,
        )
        self.assertTrue(r["alerta"])
        self.assertEqual([f["metodo"] for f in r["tareas"] if f["alerta"]], ["sgc.tasks.rota"])
        # La alarmada va primero: es lo que quien lee tiene que mirar.
        self.assertEqual(r["tareas"][0]["metodo"], "sgc.tasks.rota")

    def test_una_tarea_detenida_avisa_aunque_sea_reciente(self):
        r = latido.evaluar([tarea(horas=1, detenida=1)], AHORA, 48)
        self.assertTrue(r["alerta"])

    def test_scheduler_desactivado_avisa_aunque_las_marcas_sean_recientes(self):
        r = latido.evaluar([tarea(horas=1)], AHORA, 48, scheduler_apagado=True)
        self.assertTrue(r["alerta"])


class TestSinMarca(unittest.TestCase):
    def test_instalacion_recien_hecha_tiene_margen(self):
        r = latido.evaluar([tarea(horas=None, alta=AHORA - timedelta(hours=3), estado=None)], AHORA, 48)
        self.assertFalse(r["alerta"])

    def test_instalacion_de_dias_que_nunca_corrio_avisa(self):
        r = latido.evaluar([tarea(horas=None, alta=AHORA - timedelta(days=5), estado=None)], AHORA, 48)
        self.assertTrue(r["alerta"])
        self.assertTrue(r["tareas"][0]["nunca"])
        self.assertIsNone(r["ultima_ok"])

    def test_sin_tareas_no_hay_nada_que_vigilar(self):
        self.assertFalse(latido.evaluar([], AHORA, 48)["alerta"])


class TestFrecuencias(unittest.TestCase):
    def test_una_semanal_no_esta_atrasada_a_las_72_horas(self):
        self.assertFalse(latido.evaluar([tarea(horas=72, frecuencia="Weekly")], AHORA, 48)["alerta"])

    def test_una_semanal_si_a_los_nueve_dias(self):
        self.assertTrue(latido.evaluar([tarea(horas=24 * 9, frecuencia="Weekly")], AHORA, 48)["alerta"])

    def test_las_variantes_long_cuentan_como_su_frecuencia(self):
        self.assertEqual(latido.periodo_horas("Daily Long"), 24)
        self.assertEqual(latido.periodo_horas("Weekly Long"), 168)
        self.assertEqual(latido.periodo_horas("Cron"), 24)
        self.assertEqual(latido.umbral_tarea(48, "Daily"), 48)
        self.assertEqual(latido.umbral_tarea(48, "Hourly"), 48)


if __name__ == "__main__":
    unittest.main()
