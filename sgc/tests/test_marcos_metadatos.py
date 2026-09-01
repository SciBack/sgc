# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Metadatos normativos de los Marco Normativo — decisión de `f17_alcance_marcos`.

Se testea la DECISIÓN (qué campos se fijan y cuáles se respetan), no la
escritura: `_cambios_de_metadatos` y `_reglas_a_fijar` son funciones puras a
propósito, para poder probarlas sin sitio y sin residuo. Llamar a `run()` desde
un test comitearía de verdad —hace `frappe.db.commit()`, como corresponde a un
script de setup— y rompería el rollback de `IntegrationTestCase`.

Lo que se protege aquí:
  - que el marco de licenciamiento deje de llamarse por su código engañoso;
  - que una segunda pasada no reescriba nada (idempotencia);
  - que un texto escrito a mano que ya dice lo correcto NO se pise;
  - que `codigo` (la clave primaria) nunca entre en los campos a fijar;
  - que los dos modelos Coneau declaren umbrales de excelencia DISTINTOS
    (16 en programas, 20 en institucional), que es lo que la regla fija de
    `scoring.py` no puede distinguir.
"""
import frappe
from frappe.tests import IntegrationTestCase

from sgc.setup import f17_alcance_marcos as f17

CBC = "CBC-SUNEDU-2026"
PROGRAMAS = "CONEAU-Programas-2025"
INSTITUCIONAL = "CONEAU-Institucional-2026"
AAA = "AAA-2019"


class IntegrationTestMarcosMetadatos(IntegrationTestCase):
    def _campos(self, codigo):
        return f17.MARCOS[codigo]["campos"]

    def _canonico(self, codigo):
        """El registro tal como lo dejaría el script: cada campo en su valor canónico."""
        return {f: spec["valor"] for f, spec in self._campos(codigo).items()}

    # -- el arreglo que motiva el paso ---------------------------------------
    def test_licenciamiento_pobre_se_corrige_entero(self):
        """Lo que hay en producción: el nombre es el código, y el año miente."""
        actual = {"nombre": CBC, "version": "2026", "nota_normativa": ""}
        cambios, respetados = f17._cambios_de_metadatos(actual, self._campos(CBC))

        self.assertEqual(set(cambios), {"nombre", "version", "nota_normativa"})
        self.assertEqual(respetados, [])
        self.assertIn("Licenciamiento Institucional", cambios["nombre"])
        self.assertEqual(cambios["version"], "2015")          # el año del MODELO, no el del código
        self.assertIn("006-2015-SUNEDU/CD", cambios["nota_normativa"])

    def test_la_nota_advierte_que_el_codigo_no_es_el_ano(self):
        """El código heredado no se puede renombrar: al menos que quede dicho."""
        nota = self._campos(CBC)["nota_normativa"]["valor"]
        self.assertIn(CBC, nota)
        self.assertIn("no se renombra", nota.lower())

    def test_nunca_se_toca_el_codigo(self):
        """`codigo` es la clave primaria (`autoname: field:codigo`): renombrarlo rompe referencias."""
        for codigo in f17.MARCOS:
            self.assertNotIn("codigo", self._campos(codigo))
            self.assertNotIn("name", self._campos(codigo))

    # -- idempotencia y respeto a lo escrito a mano --------------------------
    def test_segunda_pasada_no_cambia_nada(self):
        for codigo in f17.MARCOS:
            cambios, respetados = f17._cambios_de_metadatos(self._canonico(codigo), self._campos(codigo))
            self.assertEqual(cambios, {}, codigo)
            self.assertEqual(len(respetados), len(self._campos(codigo)), codigo)

    def test_texto_propio_que_ya_dice_lo_correcto_se_respeta(self):
        """Mejor redacción humana que la nuestra: si lleva la señal, se deja."""
        actual = {
            "nombre": "Modelo de licenciamiento institucional de la Sunedu (8 CBC)",
            "version": "2015 (RCD 006-2015)",
            "nota_normativa": "Ver RCD 006-2015-SUNEDU/CD, anexo 1.",
        }
        cambios, respetados = f17._cambios_de_metadatos(actual, self._campos(CBC))
        self.assertEqual(cambios, {})
        self.assertEqual(sorted(respetados), ["nombre", "nota_normativa", "version"])

    def test_las_tildes_y_los_espacios_no_provocan_reescritura(self):
        actual = {"nombre": "MODELO  DE   LICENCIAMIENTO INSTITUCIÓNAL"}
        cambios, _ = f17._cambios_de_metadatos(actual, {"nombre": self._campos(CBC)["nombre"]})
        self.assertEqual(cambios, {})

    def test_campo_vacio_siempre_se_llena(self):
        for vacio in (None, "", "   "):
            cambios, _ = f17._cambios_de_metadatos(
                {"nombre": vacio}, {"nombre": self._campos(CBC)["nombre"]}
            )
            self.assertIn("nombre", cambios)

    # -- reglas de vigencia (declaradas, todavía no leídas por nadie) --------
    def test_licenciamiento_no_declara_anos_de_vigencia(self):
        """Se cumple o no se cumple: la Ley 32105 art. 13.4 hizo la licencia permanente."""
        self.assertIsNone(f17.MARCOS[CBC]["reglas_vigencia"])
        self.assertIsNone(f17._reglas_a_fijar("", f17.MARCOS[CBC]["reglas_vigencia"]))

    def test_la_aaa_tampoco_declara_anos_de_vigencia(self):
        """El dictamen lo vota la comisión visitante entre 8 opciones (II-8/II-9), no sale de una tabla."""
        self.assertIsNone(f17.MARCOS[AAA]["reglas_vigencia"])
        self.assertIsNone(f17._reglas_a_fijar("", f17.MARCOS[AAA]["reglas_vigencia"]))

    def test_la_aaa_es_acreditacion_institucional_y_no_se_confunde_con_el_coneau(self):
        """Acredita la identidad adventista; es independiente del Sineace y de la Sunedu."""
        self.assertEqual(f17.MARCOS[AAA]["alcance"], f17.ACRED_INSTITUCIONAL)
        nota = self._campos(AAA)["nota_normativa"]["valor"].lower()
        self.assertIn("independiente", nota)
        self.assertIn("12 estándares", nota)

    def test_los_marcos_de_referencia_no_se_cuelan_en_el_catalogo_evaluador(self):
        """ITIL, COBIT o una ley de datos orientan; no emiten un resultado de acreditación.

        Si alguno entrase en MARCOS heredaría un alcance evaluador y el sistema
        acabaría diciendo que algo está «acreditado» por ITIL.
        """
        for codigo in f17.MARCOS_DE_REFERENCIA:
            self.assertNotIn(codigo, f17.MARCOS, codigo)

    def test_umbrales_de_excelencia_distintos_por_modelo(self):
        def umbral(codigo):
            tramos = f17.MARCOS[codigo]["reglas_vigencia"]["tramos"]
            return next(t["puntaje_excelencia_minimo"] for t in tramos if t["anios"] == 8)

        self.assertEqual(umbral(PROGRAMAS), 16)
        self.assertEqual(umbral(INSTITUCIONAL), 20)

    def test_los_resultados_declarados_existen_en_el_desplegable(self):
        """Si el JSON nombra un resultado que el Select no tiene, no sirve para nada."""
        opciones = frappe.get_meta("Autoevaluacion").get_field("vigencia_propuesta").options.split("\n")
        for codigo in (PROGRAMAS, INSTITUCIONAL):
            for tramo in f17.MARCOS[codigo]["reglas_vigencia"]["tramos"]:
                self.assertIn(tramo["resultado"], opciones, codigo)

    def test_las_reglas_se_pueblan_solo_si_el_campo_esta_vacio(self):
        reglas = f17.MARCOS[PROGRAMAS]["reglas_vigencia"]
        for vacio in (None, "", "{}", {}):
            self.assertIsNotNone(f17._reglas_a_fijar(vacio, reglas), repr(vacio))
        for ocupado in ('{"tramos": []}', {"tramos": []}):
            self.assertIsNone(f17._reglas_a_fijar(ocupado, reglas), repr(ocupado))

    # -- coherencia del catálogo --------------------------------------------
    def test_todo_marco_conocido_declara_un_alcance_valido(self):
        validos = {f17.LICENCIAMIENTO, f17.ACRED_PROGRAMA, f17.ACRED_INSTITUCIONAL}
        for codigo, datos in f17.MARCOS.items():
            self.assertIn(datos["alcance"], validos, codigo)
        self.assertEqual(f17.ALCANCE_POR_MARCO[CBC], f17.LICENCIAMIENTO)
