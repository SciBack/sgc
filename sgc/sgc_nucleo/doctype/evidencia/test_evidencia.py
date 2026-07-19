# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Tests de integración de M09 — Evidencia (sgc.sgc_nucleo.doctype.evidencia).

Cubre la lógica de negocio del controlador `Evidencia`:

- Código EVD-AAAA-NNNN correlativo por año, robusto a borrados (max sufijo + 1,
  nunca `count`, para no reusar un número tras borrar una evidencia intermedia).
- Regla de soporte: una Evidencia de tipo "Enlace" exige `enlace_url`; cualquier
  otro tipo exige `archivo`.
- Una Evidencia no puede pasar a "Valida" sin al menos una Trazabilidad.
- Autocompletado de `cargado_por` y `fecha_carga` en el alta.
- Marcado automático a "Vencida" cuando la vigencia expiró.
- Helper `evidencias_de_elemento` (consulta inversa vía Trazabilidad).

Nota: las evidencias con soporte se crean como tipo "Enlace" + `enlace_url`
porque en el entorno de test no se adjunta un File real; la regla de soporte del
controlador exige `archivo` para cualquier tipo distinto de "Enlace".
"""

import re

import frappe
from frappe.tests import IntegrationTestCase
from frappe.utils import add_days, getdate, nowdate

from sgc.sgc_nucleo.doctype.evidencia.evidencia import evidencias_de_elemento
from sgc.tests import factories


EXTRA_TEST_RECORD_DEPENDENCIES = []
IGNORE_TEST_RECORD_DEPENDENCIES = []


class IntegrationTestEvidencia(IntegrationTestCase):
    """Integration tests para el controlador Evidencia (M09)."""

    def setUp(self):
        # Árbol base: 1 estándar con 2 criterios (elementos del marco a los que
        # anclar las evidencias vía Trazabilidad).
        self.arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=2)
        estandar = self.arbol["estandares"][0]
        self.criterios = self.arbol["criterios"][estandar]

    # ------------------------------------------------------------------ helpers
    def _nueva_evidencia(self, insertar=True, **kw):
        """Crea una Evidencia SIN código (para ejercitar la autogeneración).

        Por defecto es de tipo Enlace con URL (soporte válido). `insertar=False`
        devuelve el doc sin insertar (para probar validaciones que deben fallar).
        """
        vals = {
            "doctype": "Evidencia",
            "titulo": "Evidencia de prueba",
            "tipo": "Enlace",
            "enlace_url": "https://example.test/evidencia",
        }
        vals.update(kw)
        doc = frappe.get_doc(vals)
        doc.flags.ignore_permissions = True
        if insertar:
            doc.insert(ignore_permissions=True)
        return doc

    @staticmethod
    def _sufijo(codigo):
        return int(re.search(r"(\d+)$", codigo).group(1))

    # ------------------------------------------------------------ código EVD-...
    def test_codigo_autogenerado_formato(self):
        """Sin código explícito, before_insert genera EVD-<año>-NNNN (4 dígitos)."""
        anio = getdate(nowdate()).year
        ev = self._nueva_evidencia()
        self.assertRegex(ev.codigo, rf"^EVD-{anio}-\d{{4}}$")

    def test_codigo_correlativo_incrementa(self):
        """Dos altas consecutivas del mismo año incrementan el correlativo en 1."""
        ev1 = self._nueva_evidencia()
        ev2 = self._nueva_evidencia()
        self.assertEqual(self._sufijo(ev2.codigo), self._sufijo(ev1.codigo) + 1)

    def test_codigo_robusto_a_borrado_intermedio(self):
        """Tras borrar una evidencia, el siguiente código es max+1, NO count.

        Si usara `count`, borrar la del medio haría reusar un número existente y
        chocar con el índice `unique`. El correlativo debe seguir avanzando.
        """
        ev1 = self._nueva_evidencia()
        ev2 = self._nueva_evidencia()
        base = self._sufijo(ev1.codigo)
        self.assertEqual(self._sufijo(ev2.codigo), base + 1)

        # Borrar la más antigua (queda un "hueco" en la numeración).
        frappe.delete_doc("Evidencia", ev1.name, force=True, ignore_permissions=True)

        ev3 = self._nueva_evidencia()
        # max sufijo vigente = base+1 (ev2) -> ev3 = base+2, no reusa base.
        self.assertEqual(self._sufijo(ev3.codigo), base + 2)

    def test_codigo_explicito_se_respeta(self):
        """Si el alta trae `codigo`, el controlador no lo sobreescribe."""
        ev = self._nueva_evidencia(codigo="EVD-2000-9999")
        self.assertEqual(ev.codigo, "EVD-2000-9999")

    # --------------------------------------------------------------- soporte M09
    def test_soporte_enlace_sin_url_falla(self):
        """Tipo Enlace sin enlace_url -> ValidationError."""
        with self.assertRaises(frappe.ValidationError):
            self._nueva_evidencia(tipo="Enlace", enlace_url=None)

    def test_soporte_documento_sin_archivo_falla(self):
        """Tipo Documento sin archivo adjunto -> ValidationError."""
        with self.assertRaises(frappe.ValidationError):
            self._nueva_evidencia(tipo="Documento", enlace_url=None, archivo=None)

    def test_soporte_enlace_con_url_ok(self):
        """Camino feliz: tipo Enlace + URL inserta y arranca en Pendiente."""
        ev = self._nueva_evidencia(tipo="Enlace", enlace_url="https://x.test/e")
        self.assertTrue(frappe.db.exists("Evidencia", ev.name))
        self.assertEqual(ev.estado, "Pendiente")

    # ------------------------------------------------ autocompletado de metadatos
    def test_autocompleta_cargado_por_y_fecha(self):
        """before_insert rellena cargado_por (usuario de sesión) y fecha_carga."""
        ev = self._nueva_evidencia()
        self.assertEqual(ev.cargado_por, frappe.session.user)
        self.assertTrue(ev.fecha_carga)

    # ------------------------------------------------ trazabilidad para "Valida"
    def test_valida_sin_trazabilidad_falla(self):
        """Pasar a Valida sin ninguna Trazabilidad que la ancle -> ValidationError."""
        ev = self._nueva_evidencia()  # arranca Pendiente
        ev.estado = "Valida"
        with self.assertRaises(frappe.ValidationError):
            ev.save(ignore_permissions=True)

    def test_valida_con_trazabilidad_ok(self):
        """Con >=1 Trazabilidad a un criterio, sí puede marcarse Valida."""
        ev = self._nueva_evidencia()
        factories.crear_trazabilidad(ev, elemento_marco=self.criterios[0])
        ev.estado = "Valida"
        ev.save(ignore_permissions=True)
        self.assertEqual(frappe.db.get_value("Evidencia", ev.name, "estado"), "Valida")

    def test_insertar_directo_en_estado_no_inicial_falla(self):
        """Con workflow activo (f13), Frappe exige insertar siempre en el primer
        estado ("Pendiente") -- insertar directo en "Valida" u otro estado no
        inicial es rechazado por el motor de workflow antes de llegar a la
        validación de trazabilidad. Reemplaza al viejo
        `test_valida_al_insertar_no_exige_trazabilidad`, escrito cuando
        Evidencia todavía no tenía workflow (Fase 2, hallazgo H2).
        """
        with self.assertRaises(frappe.ValidationError):
            self._nueva_evidencia(estado="Valida")

    # ------------------------------------------------------- vencimiento vigencia
    def test_marca_vencida_al_expirar(self):
        """vigencia_hasta en el pasado -> estado pasa a Vencida en validate."""
        ayer = add_days(nowdate(), -1)
        ev = self._nueva_evidencia(vigencia_hasta=ayer)
        self.assertEqual(ev.estado, "Vencida")

    def test_vigencia_futura_conserva_pendiente(self):
        """vigencia_hasta en el futuro -> no toca el estado (sigue Pendiente)."""
        maniana = add_days(nowdate(), 30)
        ev = self._nueva_evidencia(vigencia_hasta=maniana)
        self.assertEqual(ev.estado, "Pendiente")

    def test_vencida_solo_desde_pendiente_o_valida(self):
        """Una evidencia Observada que expira NO se fuerza a Vencida.

        `_marcar_vencida_si_expiro` solo actúa sobre Pendiente/Valida; otros
        estados de gestión (Observada/Subsanada) se conservan. Con workflow
        activo (f13) solo se puede llegar a "Observada" transicionando desde
        Pendiente vía `.save()` (insertar directo en un estado no inicial está
        bloqueado por el motor de workflow) -- no directo al insertar.
        """
        ev = self._nueva_evidencia()  # arranca Pendiente
        ev.estado = "Observada"
        ev.save(ignore_permissions=True)
        self.assertEqual(ev.estado, "Observada")

        ayer = add_days(nowdate(), -1)
        ev.vigencia_hasta = ayer
        ev.save(ignore_permissions=True)
        self.assertEqual(ev.estado, "Observada")

    # ----------------------------------------------- helper evidencias_de_elemento
    def test_evidencias_de_elemento_devuelve_las_vinculadas(self):
        """Devuelve solo las evidencias trazadas al criterio consultado, por código."""
        crit_a, crit_b = self.criterios[0], self.criterios[1]

        ev1 = self._nueva_evidencia(codigo="EVD-2100-0001", titulo="A")
        ev2 = self._nueva_evidencia(codigo="EVD-2100-0002", titulo="B")
        ev_otro = self._nueva_evidencia(codigo="EVD-2100-0003", titulo="C")

        factories.crear_trazabilidad(ev1, elemento_marco=crit_a)
        factories.crear_trazabilidad(ev2, elemento_marco=crit_a)
        factories.crear_trazabilidad(ev_otro, elemento_marco=crit_b)

        resultado = evidencias_de_elemento(crit_a)
        names = [r["name"] for r in resultado]

        self.assertEqual(set(names), {ev1.name, ev2.name})
        self.assertNotIn(ev_otro.name, names)
        # order_by="codigo": EVD-2100-0001 antes que EVD-2100-0002.
        self.assertEqual(names, [ev1.name, ev2.name])

    def test_evidencias_de_elemento_sin_trazas_devuelve_vacio(self):
        """Un criterio sin ninguna Trazabilidad devuelve lista vacía."""
        # Criterio de un marco PROPIO (prefijo único): el criterio compartido
        # self.criterios[0] lo traza otro test de la clase, y el aislamiento de
        # datos idempotentes entre tests no siempre lo revierte.
        arbol = factories.crear_marco_prueba(n_estandares=1, n_criterios=1, prefijo="TEST-SINTRAZA")
        crit = arbol["criterios"][arbol["estandares"][0]][0]
        self.assertEqual(evidencias_de_elemento(crit), [])
