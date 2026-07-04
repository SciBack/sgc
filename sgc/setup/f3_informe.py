"""F3 informe — crea el Print Format "Informe de Autoevaluacion SINEACE" (idempotente).

Contrato: insumo D (`doc/specs/sgc-frappe/insumos/D-informe-e-indicadores.md`), Parte 1.
Genera el formato oficial SINEACE.DEA.F.04 (Informe Final de Autoevaluación) como
Print Format Jinja -> PDF con el motor Chrome de Frappe v16 (soporta flexbox/CSS moderno).

Diseño (verificado contra la Directiva 043-2023 §9.1.4 — F.04 son 6 secciones):
  Portada (membrete UPeU, título, programa/sede/periodo/marco)
  1. Datos informativos     (tabla fija del formato)
  2. Resumen de valoración  (matriz-resumen de los 10 estándares con semáforo + vigencia)
  4. Resultados             (loop por estándar: badge de nivel, criterios, evidencias)
  6. Anexo de evidencias    (tabla consolidada evidencia -> documento controlado)

La plantilla NO consulta la BD: llama al método whitelisted `doc.datos_informe()`
(= `sgc.informe.consolidar`), contrato tipado reservado también para MCP. Toda la
lógica de niveles/semáforo/evidencias vive en Python; el Jinja solo itera.

Idempotente: si el Print Format ya existe, actualiza su `html` (y campos clave);
si no, lo crea. `standard="No"` para que se guarde en DB y sea editable.

Ejecutar (lo hace el orquestador):
    bench --site sgc.localhost execute sgc.setup.f3_informe.run
"""
import frappe

PRINT_FORMAT_NAME = "Informe de Autoevaluacion SINEACE"
DOCTYPE = "Autoevaluacion"


# ===========================================================================
# Plantilla Jinja del Print Format
# ===========================================================================
# Nota membrete: se deja un <img> con la ruta esperada del logo en /files/.
# Súbelo una vez a File (público) como `membrete-upeu.png`; si no existe, el
# navegador muestra el alt y el texto del membrete igual imprime. (Ver el
# comentario  {# LOGO UPeU #}  más abajo para cambiar la ruta.)

HTML = r"""
{# ==== El contrato tipado: un solo punto de datos (= sgc.informe.consolidar) ==== #}
{%- set data = doc.datos_informe() -%}
{%- set cab = data.cabecera -%}

<style>
  .sgc-informe { font-family: "Helvetica Neue", Arial, sans-serif; color: #1f2328;
                 font-size: 11px; line-height: 1.5; }
  .sgc-informe h1, .sgc-informe h2, .sgc-informe h3, .sgc-informe h4 { margin: 0 0 .35rem; }
  .sgc-informe table { width: 100%; border-collapse: collapse; margin: .5rem 0 1rem; }
  .sgc-informe th, .sgc-informe td { border: 1px solid #d0d7de; padding: 5px 8px;
                 text-align: left; vertical-align: top; }
  .sgc-informe th { background: #f6f8fa; font-weight: 600; }

  /* Portada */
  .portada { text-align: center; padding: 3.5rem 1rem 2rem; page-break-after: always; }
  .portada .membrete { display: flex; align-items: center; justify-content: center;
                 gap: 14px; margin-bottom: 2.5rem; }
  .portada .membrete img { height: 64px; }
  .portada .membrete .inst { text-align: left; font-size: 12px; line-height: 1.35;
                 color: #24292f; }
  .portada .membrete .inst b { display: block; font-size: 14px; letter-spacing: .3px; }
  .portada h1 { font-size: 22px; margin-top: 1.5rem; color: #0b3d2e; }
  .portada .prog { font-size: 16px; font-weight: 600; margin-top: .75rem; }
  .portada .meta { margin-top: 2rem; font-size: 12px; color: #57606a; }
  .portada .formato { margin-top: 2.5rem; font-size: 11px; color: #57606a; }

  /* Secciones */
  .seccion { margin: 1.25rem 0; }
  .seccion > h3 { font-size: 14px; border-bottom: 2px solid #0b3d2e;
                 padding-bottom: 3px; color: #0b3d2e; }

  /* Badges de nivel / semáforo */
  .badge { display: inline-block; padding: 2px 10px; border-radius: 10px;
                 font-weight: 700; font-size: 11px; color: #fff; }
  .sem-verde { background: #1a7f37; }
  .sem-ambar { background: #bf8700; }
  .sem-rojo  { background: #cf222e; }
  .sem-gris  { background: #57606a; }
  .punto { font-size: 15px; line-height: 1; }
  .p-verde { color: #1a7f37; } .p-ambar { color: #bf8700; }
  .p-rojo  { color: #cf222e; } .p-gris  { color: #57606a; }

  /* Bloque por estándar */
  .estandar { margin: 1rem 0 1.5rem; page-break-inside: avoid; }
  .estandar .cab { display: flex; align-items: baseline; justify-content: space-between;
                 gap: 10px; border-left: 4px solid #0b3d2e; padding-left: 10px; }
  .estandar .cab h4 { font-size: 13px; }
  .estandar .analisis { font-style: italic; color: #444c56; margin: .4rem 0 .6rem; }
  .no-dato { color: #57606a; font-style: italic; }
  .firma { margin-top: 3rem; text-align: center; }
  .firma .linea { border-top: 1px solid #1f2328; width: 260px; margin: 0 auto 4px; }
</style>

<div class="sgc-informe">

  {# =================== PORTADA (forma libre, membrete UPeU) =================== #}
  <div class="portada">
    <div class="membrete">
      {# LOGO UPeU: sube el escudo como File público y ajusta la ruta si cambia #}
      <img src="/files/membrete-upeu.png" alt="UPeU">
      <div class="inst">
        <b>UNIVERSIDAD PERUANA UNIÓN</b>
        Dirección de Gestión de la Calidad
      </div>
    </div>

    <h1>Informe de Autoevaluación con fines de acreditación</h1>
    {%- if cab.programa %}<div class="prog">{{ cab.programa }}</div>{%- endif %}
    {%- if cab.escuela %}<div>{{ cab.escuela }}</div>{%- endif %}

    <div class="meta">
      {%- if cab.sede %}Sede: {{ cab.sede }}<br>{%- endif %}
      {%- if cab.periodo %}Periodo académico: {{ cab.periodo }}<br>{%- endif %}
      Marco de evaluación: {{ cab.marco_nombre }}{% if cab.ente %} ({{ cab.ente }}){% endif %}
    </div>

    <div class="formato">
      Formato SINEACE.DEA.F.04 — Informe Final de Autoevaluación<br>
      {{ cab.codigo }} · {{ cab.fecha }}
    </div>
  </div>

  {# =================== 1. DATOS INFORMATIVOS =================== #}
  <div class="seccion">
    <h3>1. Datos informativos</h3>
    <table>
      <tr><th style="width:32%">Institución</th><td>{{ cab.institucion }}</td></tr>
      <tr><th>Programa</th><td>{{ cab.programa or "—" }}</td></tr>
      <tr><th>Escuela profesional</th><td>{{ cab.escuela or "—" }}</td></tr>
      <tr><th>Tipo de acreditación</th><td>Programa de estudios ({{ cab.ente or "CONEAU" }})</td></tr>
      <tr><th>Sede / Filial</th><td>{{ cab.sede or "—" }}</td></tr>
      <tr><th>Marco de evaluación</th><td>{{ cab.marco_nombre }}</td></tr>
      <tr><th>Periodo académico</th><td>{{ cab.periodo or "—" }}</td></tr>
      {%- if cab.alcance %}<tr><th>Alcance</th><td>{{ cab.alcance }}</td></tr>{%- endif %}
      <tr><th>Fecha de presentación</th><td>{{ cab.fecha }}</td></tr>
      <tr><th>Estado de la autoevaluación</th><td>{{ cab.estado }}</td></tr>
    </table>
  </div>

  {# =================== 2. RESUMEN DE VALORACIÓN (matriz-resumen) =================== #}
  <div class="seccion">
    <h3>2. Resumen de la valoración</h3>
    <table>
      <tr><th style="width:70%">Estándar</th><th>Valoración</th></tr>
      {%- for r in data.resumen_valoracion %}
      <tr>
        <td>{{ r.codigo }}</td>
        <td>
          <span class="badge sem-{{ r.semaforo.color }}">{{ r.nivel }}</span>
        </td>
      </tr>
      {%- endfor %}
      <tr>
        <th>Vigencia proyectada</th>
        <td><b>{{ data.vigencia.texto }}</b>
          {%- if data.vigencia.oficial %} <span class="no-dato">(oficial)</span>
          {%- elif data.vigencia.propuesta %} <span class="no-dato">(propuesta por el motor)</span>
          {%- endif %}
        </td>
      </tr>
    </table>
    <p class="no-dato">Escala: NL = No logrado (rojo) · L = Logrado (ámbar) · LP = Logrado plenamente (verde).</p>
  </div>

  {# =================== 4. RESULTADOS DE LA AUTOEVALUACIÓN =================== #}
  <div class="seccion">
    <h3>4. Resultados de la autoevaluación</h3>

    {%- for e in data.estandares %}
    <div class="estandar">
      <div class="cab">
        <h4>Estándar {{ e.codigo }}{% if e.denominacion %} — {{ e.denominacion }}{% endif %}</h4>
        <span class="badge sem-{{ e.semaforo.color }}">
          {{ e.nivel }}{% if not e.confirmado and e.nivel != "Sin valorar" %} · propuesto{% endif %}
        </span>
      </div>

      {%- if e.texto_oficial %}<p class="analisis">{{ e.texto_oficial }}</p>{%- endif %}
      {%- if e.justificacion %}<p>{{ e.justificacion }}</p>{%- endif %}

      {# Criterios del estándar #}
      {%- if e.criterios %}
      <table>
        <tr><th style="width:12%">Criterio</th><th style="width:48%">Denominación</th>
            <th style="width:20%">Cumple</th><th>Observación</th></tr>
        {%- for c in e.criterios %}
        <tr>
          <td>{{ c.ref_id }}</td>
          <td>{{ c.denominacion }}</td>
          <td>{{ c.cumple }}</td>
          <td>{{ c.observacion }}{% if c.debilidad %}<br><i>Debilidad/OM:</i> {{ c.debilidad }}{% endif %}</td>
        </tr>
        {%- endfor %}
      </table>
      {%- else %}
      <p class="no-dato">Sin criterios registrados para este estándar.</p>
      {%- endif %}

      {# Evidencias del estándar #}
      {%- if e.evidencias %}
      <table>
        <tr><th style="width:14%">Evidencia</th><th style="width:50%">Título</th>
            <th style="width:20%">Documento controlado</th><th>Estado</th></tr>
        {%- for ev in e.evidencias %}
        <tr>
          <td>{{ ev.ev_id }}</td>
          <td>{{ ev.titulo }}</td>
          <td>{% if ev.doc_sgc %}{{ ev.doc_sgc }}{% if ev.version %} v{{ ev.version }}{% endif %}{% else %}—{% endif %}</td>
          <td>{{ ev.estado }}</td>
        </tr>
        {%- endfor %}
      </table>
      {%- endif %}
    </div>
    {%- endfor %}
  </div>

  {# =================== 6. ANEXO DE EVIDENCIAS =================== #}
  <div class="seccion">
    <h3>6. Anexo — Evidencias</h3>
    {%- if data.todas_evidencias %}
    <table>
      <tr><th style="width:14%">Cód.</th><th style="width:46%">Evidencia</th>
          <th style="width:24%">Documento controlado (Mayan)</th><th>Estado</th></tr>
      {%- for ev in data.todas_evidencias %}
      <tr>
        <td>{{ ev.ev_id }}</td>
        <td>{{ ev.titulo }}</td>
        <td>{% if ev.doc_sgc %}{{ ev.doc_sgc }}{% if ev.version %} v{{ ev.version }}{% endif %}{% else %}—{% endif %}</td>
        <td>{{ ev.estado }}</td>
      </tr>
      {%- endfor %}
    </table>
    {%- else %}
    <p class="no-dato">No hay evidencias vinculadas por trazabilidad.</p>
    {%- endif %}
  </div>

  {# =================== FIRMA (Presidente del Comité de Calidad) =================== #}
  <div class="firma">
    <div class="linea"></div>
    Presidente del Comité de Calidad<br>
    <span class="no-dato">{{ cab.institucion }} — Dirección de Gestión de la Calidad</span>
  </div>

</div>
"""


# ===========================================================================
# Creación / actualización idempotente del Print Format
# ===========================================================================

def run():
    """Crea o actualiza el Print Format del informe SINEACE. Idempotente."""
    campos = {
        "doc_type": DOCTYPE,
        "print_format_type": "Jinja",
        "standard": "No",          # editable, se guarda en DB (no en código)
        "raw_printing": 0,
        "custom_format": 1,        # usa `html` como plantilla completa (Jinja)
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
    print("Print Format '{0}' {1}  (doc_type={2}, type=Jinja, standard=No)".format(
        PRINT_FORMAT_NAME, accion, DOCTYPE))
    return {"print_format": PRINT_FORMAT_NAME, "accion": accion}
