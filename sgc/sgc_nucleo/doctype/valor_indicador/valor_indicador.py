"""Invariantes compartidas por Desk, REST, importaciones e ingesta."""
import math

import frappe
from frappe.model.document import Document
from frappe.utils import add_days, now_datetime, nowdate

# El análisis del periodo: se escribe aunque la medición esté protegida (viene de
# la ingesta) o su periodo esté cerrado, porque no cambia la medición.
CAMPOS_ANALISIS = ("analisis", "analizado_por", "fecha_analisis")
# Lo que Frappe cambia solo en cada guardado: no cuenta como modificar la medición.
_VOLATILES = {"modified", "modified_by", "semaforo", *CAMPOS_ANALISIS}
DIAS_TAREA_ANALISIS = 7


def ficha_de(indicador):
    """La ficha del indicador, con lo que el análisis necesita."""
    if not indicador:
        return None
    return frappe.db.get_value(
        "Ficha Indicador", {"indicador": indicador}, ["name", "exige_analisis", "responsable"], as_dict=True
    )


class ValorIndicador(Document):
    def validate(self):
        from sgc.ingesta import en_ingesta
        from sgc.ingesta_contrato import ErrorContrato, evaluar_reglas
        from sgc.semaforo_indicador import calcular as calcular_semaforo

        if self.valor_num is not None and not math.isfinite(float(self.valor_num)):
            frappe.throw('El valor de indicador debe ser finito')

        # El semáforo se calcula ANTES del corte por ingesta de más abajo. Si se
        # calculara después, las mediciones que entran por la API —que son la vía
        # del DW, o sea la mayoría— se guardarían sin él, y el cumplimiento solo
        # se vería en lo tecleado a mano. Es un valor derivado, no una validación:
        # su sitio es aquí arriba.
        self.semaforo = calcular_semaforo(self)
        self._sellar_analisis()
        anterior = self.get_doc_before_save()
        if anterior and self._solo_cambia_el_analisis(anterior):
            return
        self._exigir_analisis()
        if self.programa_sede and self.unidad_organica:
            frappe.throw('Una medición no puede pertenecer a dos ámbitos')
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

    def after_insert(self):
        # La próxima medición de su ficha avanza un periodo (#92). Va aquí y no en
        # validate porque validate sale antes de tiempo en la ingesta, que es la
        # vía principal de las mediciones.
        from sgc.sgc_estructura.doctype.ficha_indicador.ficha_indicador import avanzar_proxima_medicion

        avanzar_proxima_medicion(self.indicador, self.fecha)

    def on_update(self):
        sincronizar_tarea_analisis(self)

    # ---------------------------------------------------------------- análisis
    def _sellar_analisis(self):
        """Quién analizó y cuándo lo pone el sistema, al escribir o cambiar el texto."""
        anterior = self.get_doc_before_save()
        texto = (self.analisis or "").strip()
        previo = ((anterior.analisis if anterior else None) or "").strip()
        if texto != previo:
            self.analizado_por = frappe.session.user if texto else None
            self.fecha_analisis = now_datetime() if texto else None
        elif anterior:
            self.analizado_por = anterior.analizado_por
            self.fecha_analisis = anterior.fecha_analisis

    def _solo_cambia_el_analisis(self, anterior):
        for campo in self.meta.get_valid_columns():
            if campo in _VOLATILES:
                continue
            if self.get(campo) != anterior.get(campo):
                return False
        return True

    def _exigir_analisis(self):
        """Si la ficha lo exige, lo tecleado a mano llega con su análisis."""
        from sgc.ingesta import en_ingesta

        if en_ingesta() or (self.analisis or "").strip():
            return
        ficha = ficha_de(self.indicador)
        if ficha and ficha.exige_analisis:
            frappe.throw(
                'La ficha de este indicador exige el análisis de cada medición: escriba '
                'qué explica el resultado del periodo.',
                title='Análisis obligatorio',
            )

    def on_trash(self):
        if self.ingesta_clave:
            frappe.throw('Las mediciones de ingesta se conservan para auditoría')

    def before_rename(self, old, new, merge=False):
        if self.ingesta_clave:
            frappe.throw('La identidad de una medición de ingesta no se renombra')


def sincronizar_tarea_analisis(valor):
    """Tarea de analizar el periodo, abierta mientras el valor no tenga análisis.

    Solo si la ficha lo exige, y a nombre de su responsable. Es el camino de las
    mediciones que llegan por ingesta: se guardan sin análisis y el responsable
    recibe la tarea; se cierra sola al escribirlo.
    """
    from sgc import tareas

    ficha = ficha_de(valor.indicador)
    abierta = bool(ficha and ficha.exige_analisis and not (valor.analisis or "").strip())
    responsable = ficha.responsable if ficha else None
    descripcion = "Analizar la medición de {0}{1}.".format(
        valor.indicador, f" del periodo {valor.periodo_academico}" if valor.periodo_academico else "")
    tareas.sincronizar(valor, responsable, add_days(nowdate(), DIAS_TAREA_ANALISIS), descripcion, abierta)
