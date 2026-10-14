"""La identidad de la institución, leída al imprimir (#73, nativa desde la 1.2.0).

Los formatos de impresión del SGC son ficheros estándar, comunes a todas las instituciones:
no pueden llevar el nombre ni el logo de una. Los leen al imprimir con `sgc_identidad()`,
registrado en el hook `jinja` de Frappe:

    {% set id = sgc_identidad() %}
    {% if id.logo %}<img src="{{ id.logo | e }}">{% endif %} {{ id.institucion | e }}

La identidad se declara en `site_config.json` (`sgc_institucion`, `sgc_logo`, `sgc_app_name`):
cambiarla se nota en el siguiente PDF, sin desplegar nada.
"""

import frappe


def sgc_identidad():
	from sgc.setup.f3b_branding import _config

	c = _config()
	return frappe._dict(institucion=c["institucion"], logo=c["logo"], app_name=c["app_name"])
