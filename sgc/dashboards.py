"""Métodos de cálculo de los cuadros de mando (issue #30).

Los Number Card de tipo `Document Type` cubren casi todo con filtros estáticos.
Lo que no cubren es **el vencimiento**: comparar una fecha de compromiso con la
de hoy. Frappe tiene un campo `dynamic_filters_json` para eso, pero no se pudo
verificar dónde ni cómo se evalúa, y un cuadro que muestra un número equivocado
es peor que no mostrarlo. Por eso esos tres se calculan aquí, con `type="Custom"`.

⚠️ REGLA INNEGOCIABLE DE ESTE MÓDULO ⚠️

Todas las consultas usan `frappe.get_list`, **nunca** `frappe.get_all` ni
`frappe.db.count`.

En un Number Card de tipo `Custom`, Frappe comprueba que el usuario tenga lectura
sobre el `document_type` declarado (`number_card.py:115`), pero **no filtra los
registros por él**: eso lo hace la consulta. `get_all` y `db.count` ignoran
permisos por diseño, así que con ellos el cuadro contaría documentos de unidades
o programas que ese usuario no puede ver, y el número delataría información que
la lista correspondiente le oculta.

`get_list` aplica `permission_query_conditions`, que es donde vive el aislamiento
por `Programa Sede` del SGC (ver `sgc/permissions.py`).

Es el mismo motivo por el que estos cuadros no usan gráficos de tipo mapa de
calor: el heatmap de Frappe consulta con `get_all`
(`frappe/desk/doctype/dashboard_chart/dashboard_chart.py:245`).
"""
import frappe
from frappe.utils import add_days, nowdate

# Estados que significan "esto ya no está pendiente". Se declaran aquí, juntos,
# porque un cuadro que cuente de más asusta y uno que cuente de menos tranquiliza
# sin motivo: los dos errores tienen coste.
ACCION_CERRADA = ("Verificada eficaz", "Verificada no eficaz")
TRATAMIENTO_CERRADO = ("Implementado", "Verificado")

DIAS_AVISO_REVISION = 30


def _contar(doctype, filtros):
    """Cuenta respetando permisos. Único punto de consulta del módulo."""
    filas = frappe.get_list(
        doctype,
        filters=filtros,
        fields=["name"],
        limit_page_length=0,
        ignore_ifnull=True,
    )
    return len(filas)


@frappe.whitelist()
def acciones_vencidas():
    """Acciones de mejora cuyo plazo pasó y que siguen sin verificarse.

    Una acción sin `fecha_compromiso` NO cuenta como vencida: no tiene plazo que
    incumplir. Que eso sea un problema distinto lo cubre la validación de
    `accion_mejora.py`, que exige la fecha al pasar a ejecución.
    """
    return _contar(
        "Accion Mejora",
        [
            ["fecha_compromiso", "<", nowdate()],
            ["fecha_compromiso", "is", "set"],
            ["estado", "not in", ACCION_CERRADA],
        ],
    )


@frappe.whitelist()
def tratamientos_riesgo_vencidos():
    """Tratamientos de riesgo con el plazo pasado y sin implementar."""
    return _contar(
        "Tratamiento Riesgo",
        [
            ["fecha_compromiso", "<", nowdate()],
            ["fecha_compromiso", "is", "set"],
            ["estado", "not in", TRATAMIENTO_CERRADO],
        ],
    )


@frappe.whitelist()
def documentos_por_revisar():
    """Documentos controlados cuya revisión vence en los próximos 30 días.

    Incluye los ya vencidos: un documento con la revisión pasada es más urgente
    que uno que vence mañana, y dejarlo fuera del cuadro lo haría invisible justo
    cuando más importa.
    """
    return _contar(
        "Documento Controlado",
        [
            ["fecha_proxima_revision", "<=", add_days(nowdate(), DIAS_AVISO_REVISION)],
            ["fecha_proxima_revision", "is", "set"],
            ["estado", "=", "Publicado"],
        ],
    )
