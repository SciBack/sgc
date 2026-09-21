"""F22 programa PDF — Print Format del plan anual de auditorías (#66).

#38 entregó los tres informes formales como Script Reports: son *resultados*, se
consultan y se exportan. El programa anual es otra cosa: un documento que **se
aprueba y se firma** antes de ejecutar nada. Es la evidencia que un auditor
externo pide para comprobar que la organización planificó sus auditorías antes,
no después (ISO 19011 cl. 5). Un report en pantalla no sirve para eso.

Mismo contrato que `f19_ficha_pdf`: la plantilla NO consulta la base, llama a
`doc.datos_programa()` y solo itera. Y la identidad institucional sale de
`site_config` vía los marcadores `%%SGC_*%%` (#73), nunca escrita aquí.

Idempotente: si el Print Format existe, actualiza su `html`; si no, lo crea.

Ejecutar (lo hace el orquestador):
    bench --site calidad.upeu.edu.pe execute sgc.setup.f22_programa_pdf.run
"""

import frappe

from sgc.setup.f3b_branding import resolver_identidad

PRINT_FORMAT_NAME = "Plan Anual de Auditoria"
DOCTYPE = "Programa Auditoria"

HTML = """
<style>
  .sgc-pga { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2328;
             font-size: 10.5px; line-height: 1.45; }
  .sgc-pga table { width: 100%; border-collapse: collapse; margin: 6px 0 14px; }
  .sgc-pga th, .sgc-pga td { border: 1px solid #d0d7de; padding: 4px 7px;
             vertical-align: top; text-align: left; }
  .sgc-pga th { background: #f6f8fa; font-weight: 600; }

  .membrete { display: flex; align-items: center; gap: 12px;
              border-bottom: 2px solid #0b3d2e; padding-bottom: 8px; margin-bottom: 14px; }
  .membrete img { height: 46px; }
  .membrete .inst { font-size: 10px; line-height: 1.3; color: #24292f; }
  .membrete .inst b { display: block; font-size: 12.5px; letter-spacing: .3px; }
  .membrete .doc { margin-left: auto; text-align: right; font-size: 9.5px; color: #57606a; }

  h1 { font-size: 15px; margin: 0 0 2px; color: #0b3d2e; }
  .subtitulo { font-size: 10.5px; color: #57606a; margin-bottom: 10px; }
  h3 { font-size: 11.5px; margin: 14px 0 4px; color: #0b3d2e;
       border-bottom: 1.5px solid #0b3d2e; padding-bottom: 2px; }

  .campo { margin-bottom: 7px; }
  .campo .etq { font-size: 9px; text-transform: uppercase; letter-spacing: .06em;
                color: #57606a; display: block; }

  .vacio { color: #57606a; font-style: italic; padding: 8px 0; }

  .firmas { display: flex; gap: 28px; margin-top: 26px; }
  .firmas .firma { flex: 1; text-align: center; font-size: 9.5px; }
  .firmas .linea { border-top: 1px solid #24292f; margin-bottom: 4px; padding-top: 22px; }
  .firmas .rol { color: #57606a; }

  .pie { margin-top: 18px; padding-top: 6px; border-top: 1px solid #d0d7de;
         font-size: 8.5px; color: #57606a; }
</style>

{%- set d = doc.datos_programa() %}
{%- set p = d.programa %}

<div class="sgc-pga">

  <div class="membrete">
    %%SGC_LOGO_IMG%%
    <div class="inst">
      <b>%%SGC_INSTITUCION%%</b>
      Sistema de Gestión de la Calidad
    </div>
    <div class="doc">
      {{ p.codigo or p.name }}<br>
      {{ d.periodo or "—" }}<br>
      {{ p.estado or "—" }}
    </div>
  </div>

  <h1>Plan Anual de Auditorías Internas</h1>
  <div class="subtitulo">{{ p.titulo or "—" }}</div>

  <h3>1. Objetivo</h3>
  <div>{{ p.objetivo or "—" }}</div>

  <h3>2. Alcance</h3>
  <div>{{ p.alcance or "—" }}</div>

  <h3>3. Auditorías programadas ({{ d.total }})</h3>
  {%- if d.total %}
  <table>
    <thead>
      <tr>
        <th style="width:12%">Código</th>
        <th style="width:26%">Auditoría</th>
        <th style="width:13%">Tipo</th>
        <th style="width:19%">Ámbito</th>
        <th style="width:11%">Fecha plan</th>
        <th style="width:19%">Auditor líder</th>
      </tr>
    </thead>
    <tbody>
      {%- for a in d.auditorias %}
      <tr>
        <td>{{ a.name }}</td>
        <td>{{ a.titulo or "—" }}</td>
        <td>{{ a.tipo or "—" }}</td>
        <td>{{ a.unidad_organica or a.proceso or a.programa_sede or "—" }}</td>
        <td>{{ frappe.format(a.fecha_plan, {"fieldtype": "Date"}) or "—" }}</td>
        <td>{{ a.auditor_lider.full_name if a.auditor_lider else "—" }}</td>
      </tr>
      {%- endfor %}
    </tbody>
  </table>
  {%- else %}
  <div class="vacio">
    Este programa aún no tiene auditorías registradas. El marco (objetivo, alcance y
    responsable) se aprueba primero; las auditorías se programan después.
  </div>
  {%- endif %}

  <h3>4. Aprobación</h3>
  <div class="campo">
    <span class="etq">Fecha de aprobación</span>
    {{ frappe.format(p.fecha_aprobacion, {"fieldtype": "Date"}) or "Pendiente de aprobación" }}
  </div>

  <div class="firmas">
    <div class="firma">
      <div class="linea"></div>
      {{ d.responsable.full_name if d.responsable else "—" }}<br>
      <span class="rol">Responsable del programa</span>
    </div>
    <div class="firma">
      <div class="linea"></div>
      {{ d.aprobado_por.full_name if d.aprobado_por else "—" }}<br>
      <span class="rol">Aprobado por</span>
    </div>
  </div>

  <div class="pie">
    Documento generado por el Sistema de Gestión de la Calidad ·%%SGC_PIE_INSTITUCION%%
    {{ frappe.utils.formatdate(frappe.utils.nowdate(), "dd/MM/yyyy") }} ·
    Estado del programa: {{ p.estado or "—" }}
  </div>

</div>
"""


def run():
    """Crea o actualiza el Print Format del plan anual. Idempotente."""
    campos = {
        "doc_type": DOCTYPE,
        "print_format_type": "Jinja",
        "standard": "No",
        "raw_printing": 0,
        "custom_format": 1,
        "print_format_builder": 0,
        "font_size": 10,
        "margin_top": 14.0,
        "margin_bottom": 14.0,
        "margin_left": 14.0,
        "margin_right": 14.0,
        "default_print_language": "es",
        # La identidad se hornea al crear el formato (#73).
        "html": resolver_identidad(HTML),
    }

    if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        pf = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
        for clave, valor in campos.items():
            pf.set(clave, valor)
        pf.save(ignore_permissions=True)
        accion = "actualizado"
    else:
        pf = frappe.get_doc(dict(doctype="Print Format", name=PRINT_FORMAT_NAME, **campos))
        pf.insert(ignore_permissions=True)
        accion = "creado"

    # Que sea el formato por defecto: quien pulse Imprimir en un programa debe
    # obtener el plan, no el volcado estándar de campos.
    frappe.db.set_value("DocType", DOCTYPE, "default_print_format", PRINT_FORMAT_NAME)

    print(f"Print Format '{PRINT_FORMAT_NAME}' {accion} y fijado por defecto en {DOCTYPE}")
    return {"print_format": PRINT_FORMAT_NAME, "accion": accion}
