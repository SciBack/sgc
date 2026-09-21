"""Utilidades compartidas por los informes del SGC (issue #38).

## La regla que justifica este módulo

Frappe comprueba que el usuario tenga permiso de informe sobre el doctype de
referencia (`frappe/desk/query_report.py:49`), pero **no filtra las filas**: eso
depende de cómo consulte el script.

Y seis doctypes del SGC sí tienen aislamiento por ámbito declarado en
`hooks.py:174`: `Autoevaluacion`, `Hallazgo`, `No Conformidad`,
`Valoracion Criterio`, `Valoracion Estandar` y `Plan Mejora`. Un informe sobre
ellos que consulte con `frappe.get_all` enseñaría los hallazgos y las no
conformidades de programas que ese usuario no puede abrir en la lista — y encima
en formato exportable.

Por eso aquí solo hay una forma de consultar, `consultar()`, y usa `get_list`.

`get_all` no está prohibido en todo el producto: para doctypes sin aislamiento da
igual, y el informe de indicadores lo usa legítimamente (`Valor Indicador` no
está en esa lista). Lo que no puede pasar es que la elección se haga documento a
documento y por descuido.
"""
import frappe
from frappe.utils import date_diff, getdate, nowdate


def consultar(doctype, filtros, campos, orden=None):
    """Consulta respetando el aislamiento por ámbito. Único acceso a datos."""
    return frappe.get_list(
        doctype,
        filters=filtros,
        fields=campos,
        order_by=orden,
        limit=0,
        ignore_ifnull=True,
    )


def dias_de_retraso(fecha_compromiso, cerrado=False):
    """Días vencidos, o None si no aplica.

    Devuelve None —no 0— cuando no hay retraso: un 0 en la columna se lee como
    «vence hoy», y un hueco como «no aplica». No es lo mismo.
    """
    if cerrado or not fecha_compromiso:
        return None
    dias = date_diff(nowdate(), getdate(fecha_compromiso))
    return dias if dias > 0 else None


def filtro_periodo(filtros, campo="periodo_academico"):
    """Añade el periodo al filtro solo si el usuario eligió uno."""
    periodo = (filtros or {}).get("periodo_academico")
    return {campo: periodo} if periodo else {}


def aplicar_opcionales(destino, filtros, campos):
    """Copia al filtro los campos que el usuario haya rellenado."""
    for campo in campos:
        valor = (filtros or {}).get(campo)
        if valor:
            destino[campo] = valor
    return destino
