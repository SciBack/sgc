"""Portal público del SGC-UPeU (home de calidad.upeu.edu.pe).

Página pública (guest) con métricas VIVAS del sistema. El acceso del comité
no muestra formulario usuario/clave: el botón dispara el login directo M365
vía `sgc.api.acceso_m365` (OIDC Keycloak → IdP MicrosoftUPeU).
"""

import frappe

# Portal de datos abiertos (transparencia) — CKAN.
DATOS_ABIERTOS_URL = "https://datosabiertos.upeu.edu.pe"


def _count(doctype, filters=None):
    try:
        return frappe.db.count(doctype, filters) if filters else frappe.db.count(doctype)
    except Exception:
        return 0


def get_context(context):
    context.no_cache = 1
    context.title = "Sistema de Gestión de la Calidad · UPeU"
    context.body_class = "sgc-portal"

    # --- métricas públicas, vivas (no sensibles) ---
    context.n_modelos = _count("Marco Normativo")
    context.n_estandares = _count("Elemento Marco", {"tipo": "Estandar"})
    context.n_criterios = _count("Elemento Marco", {"tipo": "Criterio"})
    context.n_indicadores = _count("Indicador")
    context.n_programas = _count("Programa")

    context.datos_url = DATOS_ABIERTOS_URL
    return context
