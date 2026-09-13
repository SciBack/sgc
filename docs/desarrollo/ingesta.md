# API de ingesta de indicadores, contrato v1

Estado: candidato de implementación; no activar productores hasta migrar el sitio,
validar un piloto y registrar la configuración de Fuente Dato. La especificación
OpenAPI está en `ingesta.openapi.json`.

POST `/api/method/sgc.ingesta.publicar_lote`, autenticado con una cuenta técnica
Frappe (`Authorization: token API_KEY:API_SECRET`). El cuerpo es `{"lote": {...}}`.
La cuenta debe estar asignada en `Fuente Dato.usuario_ingesta`, la fuente Activa
y su `codigo_publicacion` debe ser único. Además se comprueban permisos de
creación/edición del documento, sus referencias y el ámbito Programa Sede.
No enviar secretos en URL, archivos versionados ni logs.

Ejemplo ficticio de `lote`:

```json
{
  "version": 1,
  "fuente_dato": "FUENTE-DEMO",
  "run_id": "extraccion-2026-09-13-01",
  "extraido_en": "2026-09-13T05:00:00Z",
  "mediciones": [{
    "indicador": "IND-DEMO",
    "periodo_academico": "2026-I",
    "valor_num": 0,
    "unidad": "%",
    "numerador": 0,
    "denominador": 20,
    "cobertura_pct": 0,
    "formula_version": "demostracion-v1",
    "estado_medicion": "Provisional",
    "corte_inicio": "2026-09-01T00:00:00Z",
    "corte_fin": "2026-09-12T23:59:59Z"
  }]
}
```

Máximo 500 mediciones y 1 000 000 bytes de contrato JSON. Campos desconocidos,
no finitos, fechas sin zona y períodos cerrados se rechazan. Un ámbito puede ser
Programa Sede, Unidad Orgánica o institucional (ambos vacíos), nunca ambos a la
vez. La clave de medición incluye fuente, indicador, período y ámbito completo.
Numerador y denominador se declaran juntos; denominador debe ser positivo.
Cobertura `null` significa desconocida; cero es un dato real. La fórmula y su
unidad son responsabilidad del productor y deben conciliarse con el catálogo.
No se interpreta ni ejecuta código de fórmulas recibido.

Las metas opcionales requieren los tres campos `meta_valor`, `meta_operador`
(`>`, `>=`, `<`, `<=`, `=`) y `meta_unidad`. Las reglas activas de fuente/indicador
se aplican por intersección: v1 ejecuta Rango y Obligatorio; otros tipos impiden
aceptar el lote hasta implementarse. Una advertencia crea Alerta Indicador; una
regla bloqueante rechaza el lote entero.

Frappe envuelve el resultado en `message`. Tanto Aceptado como Rechazado de
negocio devuelven HTTP 200: **el productor debe comprobar `message.estado`**.
El resultado contiene `lote`, `estado`, `mediciones`, `advertencias`, `errores`.
Errores de autenticación/autorización, de estructura o fallos inesperados usan
la respuesta de error Frappe, y no prometen un Lote Ingesta persistido.

Cada fuente serializa sus publicaciones mediante bloqueo de fila PostgreSQL.
Si PostgreSQL detecta conflicto de serialización al adquirir ese bloqueo, se
renueva la transacción hasta tres intentos, únicamente cuando todavía no contiene
escrituras. No se revierte trabajo previo de un llamador ni se repiten escrituras
parciales. Si persiste el conflicto, el productor recibe error y conserva su lote
para repetirlo con la misma identidad.
El POST confirma una sola transacción: no hay commits por medición. Un rechazo
de negocio guarda el lote rechazado sin mediciones; un error inesperado revierte
toda la transacción. Un mismo run_id y contenido normalizado devuelve la respuesta
guardada, incluso después de cerrar el período; contenido distinto con ese run_id
falla. Un lote rechazado corregido necesita nuevo run_id. Reordenar mediciones
no cambia su hash; omitir opcionales y declararlos null son equivalentes.

Un corte anterior no reemplaza al vigente. La adopción de datos anteriores solo
se permite si existe un único registro con la misma fuente/código, indicador,
período y ámbito. Conserva su nombre e historial Version; duplicados requieren
conciliación explícita. `datos_ingesta` conserva el contrato completo. El campo
heredado `valor_texto` no se reescribe y no debe usarse como fuente para registros
gestionados por ingesta. No se borran mediciones que falten en lotes posteriores.

Las fuentes con cuenta de ingesta o lotes no se renombran/fusionan. Los registros
administrados no se pueden editar por REST genérico/Desk ni cambiar de fuente
para eludir la API. La asignación de cuentas y permisos debe hacerse antes del
piloto, con una cuenta distinta del administrador y con alcance probado.

Validación local: `python -m unittest discover -s tests -p 'test_ingesta_contrato.py'`.
Integración Frappe/PostgreSQL: GitHub Actions, `sgc.tests.test_ingesta`. El runner
`deploy/ci_ingesta_transacciones.py` prueba peticiones WSGI con conexiones distintas,
bloqueo real observado en PostgreSQL y reversión tras primera medición/alerta.
Solo puede ejecutarse en el sitio efímero de CI. Su resultado debe estar aprobado
para el commit candidato; una prueba de repetición secuencial no lo sustituye.
