"""F19 ficha PDF — Print Format institucional de la Ficha de Caracterización.

Lo pidió la DPGC el 10-sep-2026, textual: «el cliente lo que debería visualizar es
el PDF, no el formulario editable». El formulario es para quien administra; el
documento que se entrega, revisa y archiva es este.

Y el otro requisito de la misma reunión: **las tareas salen del diagrama al
documento**. El flujograma solo muestra actividades; aquí cada procedimiento lleva
debajo su secuencia de tareas con el responsable, leída del propio BPMN. No hay
lista paralela que mantener, así que el PDF no puede contradecir al diagrama.

La plantilla NO consulta la BD: llama a `doc.datos_ficha()`, que resuelve en Python
el proceso, los procedimientos y sus tareas. El Jinja solo itera — mismo contrato
que `f3_informe`.

Idempotente: si el Print Format existe, actualiza su `html`; si no, lo crea.

Ejecutar (lo hace el orquestador):
    bench --site calidad.upeu.edu.pe execute sgc.setup.f19_ficha_pdf.run
"""
import frappe

PRINT_FORMAT_NAME = "Ficha de Caracterizacion UPeU"
DOCTYPE = "Ficha Caracterizacion Proceso"

# El membrete se espera en /files/membrete-upeu.png (público). Si no estuviera, el
# bloque de texto institucional imprime igual: el documento nunca sale sin cabecera.
HTML = """
<style>
  .sgc-ficha { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2328;
               font-size: 10.5px; line-height: 1.45; }
  .sgc-ficha table { width: 100%; border-collapse: collapse; margin: 6px 0 14px; }
  .sgc-ficha th, .sgc-ficha td { border: 1px solid #d0d7de; padding: 4px 7px;
               vertical-align: top; text-align: left; }
  .sgc-ficha th { background: #f6f8fa; font-weight: 600; }

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
  h4 { font-size: 10.5px; margin: 10px 0 3px; color: #24292f; }

  .campo { margin-bottom: 7px; }
  .campo .etq { font-size: 9px; text-transform: uppercase; letter-spacing: .06em;
                color: #57606a; display: block; }

  .proc { border: 1px solid #d0d7de; border-left: 3px solid #0b3d2e;
          padding: 7px 9px; margin-bottom: 10px; page-break-inside: avoid; }
  .proc .cab { font-weight: 600; font-size: 10.5px; }
  .proc .cod { font-family: "SFMono-Regular", Consolas, monospace; color: #57606a;
               font-size: 9.5px; }
  .proc table { margin: 5px 0 0; }
  .proc td.num { width: 26px; text-align: right; color: #57606a; }
  .sin { color: #8c959f; font-style: italic; }

  .firmas td { height: 46px; vertical-align: bottom; font-size: 9.5px; color: #57606a; }
  .pie { margin-top: 16px; border-top: 1px solid #d0d7de; padding-top: 5px;
         font-size: 8.5px; color: #8c959f; }
</style>

{%- set d = doc.datos_ficha() -%}

<div class="sgc-ficha">

  <div class="membrete">
    <img src="/files/membrete-upeu.png" alt="">
    <div class="inst">
      <b>UNIVERSIDAD PERUANA UNIÓN</b>
      Sistema de Gestión de la Calidad
    </div>
    <div class="doc">
      {{ doc.name }}<br>
      Versión {{ doc.version or "—" }} · {{ frappe.format(doc.fecha_emision, {"fieldtype": "Date"}) or "—" }}<br>
      {{ doc.estado or "—" }}
    </div>
  </div>

  <h1>Ficha de Caracterización de Proceso</h1>
  <div class="subtitulo">
    {%- if d.proceso -%}
      <b>{{ d.proceso.codigo }}</b> · {{ d.proceso.proceso }}
      {%- if d.proceso.nivel %} · {{ d.proceso.nivel }}{% endif -%}
      {%- if d.proceso.nivel_bpm %} · {{ d.proceso.nivel_bpm }}{% endif -%}
    {%- else -%}<span class="sin">Sin proceso enlazado</span>{%- endif -%}
  </div>

  <h3>1. Planificar</h3>
  <div class="campo"><span class="etq">Objetivo</span>{{ doc.objetivo or '<span class="sin">No declarado</span>' }}</div>
  <div class="campo"><span class="etq">Alcance</span>{{ doc.alcance or '<span class="sin">No declarado</span>' }}</div>
  <div class="campo"><span class="etq">Requisitos aplicables</span>{{ doc.requisitos_aplicables or '<span class="sin">No declarados</span>' }}</div>
  <div class="campo"><span class="etq">Recursos</span>{{ doc.recursos or '<span class="sin">No declarados</span>' }}</div>

  <h3>2. Entradas</h3>
  <table>
    <thead><tr><th style="width:32%">Proveedor</th><th style="width:28%">Unidad orgánica</th><th>Insumo</th></tr></thead>
    <tbody>
      {%- for e in d.entradas %}
      <tr><td>{{ e.proveedor or "—" }}</td><td>{{ e.unidad_organica or "—" }}</td><td>{{ e.insumo or "—" }}</td></tr>
      {%- else %}
      <tr><td colspan="3" class="sin">Sin entradas declaradas</td></tr>
      {%- endfor %}
    </tbody>
  </table>

  <h3>3. Actividades y tareas</h3>
  {%- for a in d.actividades %}
  <div class="proc">
    <div class="cab">
      {%- if a.orden %}{{ a.orden }}. {% endif -%}
      {{ a.descripcion or "—" }}
    </div>
    {%- if a.procedimiento %}
    <div class="cod">{{ a.procedimiento.codigo }} · {{ a.procedimiento.titulo }} · {{ a.procedimiento.estado or "—" }}</div>
      {%- if a.tareas %}
      <table>
        <thead><tr><th style="width:26px">Nº</th><th>Tarea</th><th style="width:34%">Responsable</th></tr></thead>
        <tbody>
          {%- for t in a.tareas %}
          <tr>
            <td class="num">{{ t.n }}</td>
            <td>{{ t.actividad }}</td>
            <td>{{ t.responsable or '<span class="sin">Sin responsable en el diagrama</span>' }}</td>
          </tr>
          {%- endfor %}
        </tbody>
      </table>
      {%- else %}
      <div class="sin" style="margin-top:4px;">El procedimiento aún no tiene diagrama con tareas legibles.</div>
      {%- endif %}
    {%- else %}
    <div class="sin">Sin procedimiento enlazado.</div>
    {%- endif %}
  </div>
  {%- else %}
  <p class="sin">Sin actividades declaradas.</p>
  {%- endfor %}

  <h3>4. Salidas</h3>
  <table>
    <thead><tr><th style="width:40%">Entregable</th><th style="width:32%">Cliente</th><th>Unidad orgánica</th></tr></thead>
    <tbody>
      {%- for s in d.salidas %}
      <tr><td>{{ s.entregable or "—" }}</td><td>{{ s.cliente or "—" }}</td><td>{{ s.unidad_organica or "—" }}</td></tr>
      {%- else %}
      <tr><td colspan="3" class="sin">Sin salidas declaradas</td></tr>
      {%- endfor %}
    </tbody>
  </table>

  <h3>5. Verificar y actuar</h3>

  <h4>Indicadores del proceso</h4>
  <table>
    <thead><tr><th style="width:20%">Código</th><th>Indicador</th><th style="width:22%">Categoría</th></tr></thead>
    <tbody>
      {%- for i in d.indicadores %}
      <tr><td class="cod">{{ i.codigo or i.name }}</td><td>{{ i.nombre or "—" }}</td><td>{{ i.categoria or "—" }}</td></tr>
      {%- else %}
      <tr><td colspan="3" class="sin">Sin indicadores declarados</td></tr>
      {%- endfor %}
    </tbody>
  </table>

  {%- if d.riesgos %}
  <h4>Riesgos</h4>
  <table><tbody>
    {%- for r in d.riesgos %}<tr><td>{{ r.get("riesgo") or r.get("descripcion") or "—" }}</td></tr>{%- endfor %}
  </tbody></table>
  {%- endif %}

  {%- if d.documentos %}
  <h4>Documentos asociados</h4>
  <table><tbody>
    {%- for x in d.documentos %}<tr><td>{{ x.get("documento") or x.get("titulo") or "—" }}</td></tr>{%- endfor %}
  </tbody></table>
  {%- endif %}

  <h3>6. Control de emisión</h3>
  <table class="firmas">
    <thead><tr><th style="width:33%">Elaborado por</th><th style="width:33%">Revisado por</th><th>Aprobado por</th></tr></thead>
    <tbody>
      <tr>
        <td>{{ frappe.db.get_value("User", doc.elaborado_por, "full_name") or doc.elaborado_por or "—" }}</td>
        <td>{{ frappe.db.get_value("User", doc.revisado_por, "full_name") or doc.revisado_por or "—" }}</td>
        <td>{{ frappe.db.get_value("User", doc.aprobado_por, "full_name") or doc.aprobado_por or "—" }}</td>
      </tr>
    </tbody>
  </table>
  {%- if doc.resolucion_aprobacion %}
  <div class="campo"><span class="etq">Resolución de aprobación</span>{{ doc.resolucion_aprobacion }}</div>
  {%- endif %}

  {%- if d.cambios %}
  <h4>Control de cambios</h4>
  <table>
    <thead><tr><th style="width:14%">Versión</th><th style="width:18%">Fecha</th><th>Descripción del cambio</th></tr></thead>
    <tbody>
      {%- for c in d.cambios %}
      <tr>
        <td>{{ c.get("version") or "—" }}</td>
        <td>{{ frappe.format(c.get("fecha"), {"fieldtype": "Date"}) or "—" }}</td>
        <td>{{ c.get("descripcion") or c.get("cambio") or "—" }}</td>
      </tr>
      {%- endfor %}
    </tbody>
  </table>
  {%- endif %}

  <div class="pie">
    Documento generado por el Sistema de Gestión de la Calidad · Universidad Peruana Unión ·
    {{ frappe.utils.formatdate(frappe.utils.nowdate(), "dd/MM/yyyy") }} ·
    Estado del documento: {{ doc.estado or "—" }}
  </div>

</div>
"""


def run():
    """Crea o actualiza el Print Format de la ficha. Idempotente."""
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
        "html": HTML,
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

    # Que sea el formato por defecto del doctype: quien pulse Imprimir obtiene el
    # documento institucional, no el volcado estándar de campos.
    frappe.db.set_value("DocType", DOCTYPE, "default_print_format", PRINT_FORMAT_NAME)
    frappe.db.commit()
    print(f"Print Format '{PRINT_FORMAT_NAME}' {accion} y fijado por defecto en {DOCTYPE}")
    return {"print_format": PRINT_FORMAT_NAME, "accion": accion}
