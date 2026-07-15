"""F6 informe CBC — crea el Print Format "Diagnostico CBC SUNEDU" (idempotente).

Genera el Informe Anual de Cumplimiento / diagnóstico de las 8 Condiciones
Básicas de Calidad (RF-A03) como Print Format Jinja -> PDF con el motor Chrome
de Frappe v16. Mismo patrón que f3_informe.py (informe de autoevaluación).

La plantilla NO consulta la BD: llama al método whitelisted
`doc.datos_diagnostico()` (= consolidado en informe_cumplimiento.py). El Jinja
solo itera. Semáforo por CBC y global con color; conteos; justificaciones.

Ejecutar:
    bench --site <site> execute sgc.setup.f6_informe_cbc.run
"""
import frappe

PRINT_FORMAT_NAME = "Diagnostico CBC SUNEDU"
DOCTYPE = "Informe Cumplimiento"

HTML = r"""
{%- set d = doc.datos_diagnostico() -%}

<style>
  .cbc { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2328;
         font-size: 11px; line-height: 1.5; }
  .cbc h1, .cbc h2, .cbc h3 { margin: 0 0 .35rem; }
  .cbc table { width: 100%; border-collapse: collapse; margin: .5rem 0 1rem; }
  .cbc th, .cbc td { border: 1px solid #d0d7de; padding: 5px 8px; text-align: left;
         vertical-align: top; }
  .cbc th { background: #f6f8fa; font-weight: 600; }

  .portada { text-align: center; padding: 3rem 1rem 2rem; page-break-after: always; }
  .portada .membrete { display: flex; align-items: center; justify-content: center;
         gap: 14px; margin-bottom: 2.5rem; }
  .portada .membrete img { height: 60px; }
  .portada .membrete .inst { text-align: left; font-size: 12px; line-height: 1.35; }
  .portada .membrete .inst b { display: block; font-size: 14px; letter-spacing: .3px; }
  .portada h1 { font-size: 21px; margin-top: 1.5rem; color: #0b3d2e; }
  .portada .sub { color: #57606a; margin-top: .4rem; }

  h2.sec { font-size: 14px; border-bottom: 2px solid #0b3d2e; padding-bottom: 3px;
         margin: 1.4rem 0 .6rem; color: #0b3d2e; }

  .badge { display: inline-block; padding: 2px 10px; border-radius: 10px;
         font-size: 10px; font-weight: 700; color: #fff; }
  .b-verde { background: #1a7f37; }
  .b-ambar { background: #bf8700; }
  .b-rojo  { background: #cf222e; }
  .b-gris  { background: #8c959f; }

  .resumen-cards { display: flex; gap: 10px; margin: .6rem 0 1rem; }
  .card { flex: 1; border: 1px solid #d0d7de; border-radius: 6px; padding: 10px 12px;
         text-align: center; }
  .card .n { font-size: 22px; font-weight: 700; display: block; }
  .card .l { font-size: 10px; color: #57606a; text-transform: uppercase;
         letter-spacing: .3px; }
  .no-dato { color: #8c959f; font-style: italic; }
  .just { color: #57606a; font-size: 10px; }
</style>

{%- macro sem_badge(v) -%}
  {%- if v == "Verde" -%}<span class="badge b-verde">VERDE</span>
  {%- elif v in ("Ámbar", "Ambar") -%}<span class="badge b-ambar">ÁMBAR</span>
  {%- elif v == "Rojo" -%}<span class="badge b-rojo">ROJO</span>
  {%- else -%}<span class="badge b-gris">SIN DATO</span>{%- endif -%}
{%- endmacro -%}

{%- macro cumple_badge(v) -%}
  {%- if v == "Cumple" -%}<span class="badge b-verde">Cumple</span>
  {%- elif v == "Cumple parcial" -%}<span class="badge b-ambar">Cumple parcial</span>
  {%- elif v == "No cumple" -%}<span class="badge b-rojo">No cumple</span>
  {%- else -%}<span class="badge b-gris">Sin evaluar</span>{%- endif -%}
{%- endmacro -%}

<div class="cbc">

  <div class="portada">
    <div class="membrete">
      {# LOGO UPeU — mismo File público que el informe de autoevaluación #}
      <img src="/files/membrete-upeu.png" alt="">
      <div class="inst">
        <b>{{ d.institucion }}</b>
        Dirección de Gestión de la Calidad
      </div>
    </div>
    <h1>Informe Anual de Cumplimiento<br>de Condiciones Básicas de Calidad</h1>
    <div class="sub">Ejercicio {{ d.anio or "—" }} · Marco {{ d.marco or "CBC-SUNEDU" }}</div>
    <div class="sub">Estado del diagnóstico global: {{ sem_badge(d.semaforo) }}</div>
  </div>

  <h2 class="sec">1. Datos del informe</h2>
  <table>
    <tr><th style="width:32%">Institución</th><td>{{ d.institucion }}</td></tr>
    <tr><th>Ejercicio (año)</th><td>{{ d.anio or "—" }}</td></tr>
    <tr><th>Marco normativo</th><td>{{ d.marco or "—" }}</td></tr>
    <tr><th>Unidad orgánica</th><td>{{ d.unidad or "—" }}</td></tr>
    <tr><th>Estado</th><td>{{ d.estado or "—" }}</td></tr>
    <tr><th>Fecha de presentación</th><td>{{ d.fecha_presentacion or "—" }}</td></tr>
  </table>

  <h2 class="sec">2. Resumen del diagnóstico</h2>
  <div class="resumen-cards">
    <div class="card"><span class="n" style="color:#1a7f37">{{ d.n_cumple }}</span><span class="l">Cumple</span></div>
    <div class="card"><span class="n" style="color:#bf8700">{{ d.n_parcial }}</span><span class="l">Cumple parcial</span></div>
    <div class="card"><span class="n" style="color:#cf222e">{{ d.n_no_cumple }}</span><span class="l">No cumple</span></div>
    <div class="card"><span class="n">{{ d.total }}</span><span class="l">Total CBC</span></div>
  </div>
  <p>Semáforo global: {{ sem_badge(d.semaforo) }}
     &nbsp;<span class="just">(Rojo si alguna CBC no cumple; Ámbar si alguna cumple parcialmente; Verde si todas cumplen.)</span></p>

  <h2 class="sec">3. Estado por Condición Básica de Calidad</h2>
  <table>
    <thead>
      <tr><th style="width:12%">CBC</th><th>Condición</th><th style="width:16%">Estado</th><th style="width:34%">Justificación</th></tr>
    </thead>
    <tbody>
      {%- for c in d.condiciones %}
      <tr>
        <td><b>{{ c.codigo }}</b></td>
        <td>{{ c.denominacion }}
          {%- if c.no_conformidad %}<br><span class="just">NC: {{ c.no_conformidad }}</span>{%- endif -%}
        </td>
        <td>{{ cumple_badge(c.cumple) }}</td>
        <td>{% if c.justificacion %}{{ c.justificacion }}{% else %}<span class="no-dato">—</span>{% endif %}</td>
      </tr>
      {%- endfor %}
    </tbody>
  </table>

  {%- if d.resumen %}
  <h2 class="sec">4. Declaración / resumen</h2>
  <div>{{ d.resumen }}</div>
  {%- endif %}

  <div style="margin-top:3rem; text-align:center;">
    <div style="border-top:1px solid #24292f; width:280px; margin:0 auto; padding-top:6px;">
      Rector
      <br><span class="no-dato">{{ d.institucion }}</span>
    </div>
  </div>

</div>
"""


def run():
    """Crea o actualiza el Print Format del diagnóstico CBC. Idempotente."""
    campos = {
        "doc_type": DOCTYPE,
        "print_format_type": "Jinja",
        "standard": "No",
        "raw_printing": 0,
        "custom_format": 1,
        "print_format_builder": 0,
        "font_size": 11,
        "margin_top": 12.0,
        "margin_bottom": 12.0,
        "margin_left": 12.0,
        "margin_right": 12.0,
        "default_print_language": "es",
        "html": HTML,
    }

    if frappe.db.exists("Print Format", PRINT_FORMAT_NAME):
        pf = frappe.get_doc("Print Format", PRINT_FORMAT_NAME)
        for k, v in campos.items():
            pf.set(k, v)
        pf.save(ignore_permissions=True)
        accion = "actualizado"
    else:
        pf = frappe.get_doc(dict(doctype="Print Format", name=PRINT_FORMAT_NAME, **campos))
        pf.insert(ignore_permissions=True)
        accion = "creado"

    frappe.db.commit()
    print("Print Format '{0}' {1}  (doc_type={2}, type=Jinja)".format(
        PRINT_FORMAT_NAME, accion, DOCTYPE))
    return {"print_format": PRINT_FORMAT_NAME, "accion": accion}
