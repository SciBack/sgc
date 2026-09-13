"""Invariantes compartidas por Desk, REST, importaciones e ingesta."""
import math

import frappe
from frappe.model.document import Document


class ValorIndicador(Document):
    def validate(self):
        from sgc.ingesta import en_ingesta
        from sgc.ingesta_contrato import ErrorContrato, evaluar_reglas

        if self.valor_num is not None and not math.isfinite(float(self.valor_num)):
            frappe.throw('El valor de indicador debe ser finito')
        if self.programa_sede and self.unidad_organica:
            frappe.throw('Una medición no puede pertenecer a dos ámbitos')
        anterior = self.get_doc_before_save()
        periodos = {self.periodo_academico, anterior.periodo_academico if anterior else None}
        for periodo in periodos - {None, ''}:
            if frappe.db.get_value('Periodo Academico', periodo, 'estado') != 'abierto':
                frappe.throw('No se puede modificar una medición de un período cerrado')
        if en_ingesta():
            return
        protegida = bool(self.ingesta_clave or self.fuente_dato or self.lote_ingesta
                         or (anterior and (anterior.ingesta_clave or anterior.fuente_dato)))
        for fuente in {self.fuente, anterior.fuente if anterior else None} - {None, ''}:
            protegida = protegida or bool(frappe.db.exists('Fuente Dato', {
                'codigo_publicacion': fuente, 'usuario_ingesta': ['is', 'set']}))
        if protegida:
            frappe.throw('Esta fuente o medición se administra mediante la API de ingesta')
        # Reglas por indicador también gobiernan la edición manual; las de fuente
        # se ejecutan en la API. Nunca evaluar código Python guardado en una regla.
        reglas = frappe.get_all('Regla Validacion', filters={'activa': 1, 'indicador': self.indicador}, fields=[
            'name', 'fuente_dato', 'tipo_regla', 'campo_objetivo', 'valor_min', 'valor_max', 'severidad', 'mensaje'])
        try:
            avisos = evaluar_reglas(self.as_dict(), [r for r in reglas if not r.fuente_dato])
        except ErrorContrato as exc:
            frappe.throw(str(exc))
        for aviso in avisos:
            if aviso['severidad'] == 'Bloqueante':
                frappe.throw(aviso['mensaje'])
            frappe.msgprint(aviso['mensaje'], indicator='orange')

    def on_trash(self):
        if self.ingesta_clave:
            frappe.throw('Las mediciones de ingesta se conservan para auditoría')

    def before_rename(self, old, new, merge=False):
        if self.ingesta_clave:
            frappe.throw('La identidad de una medición de ingesta no se renombra')
