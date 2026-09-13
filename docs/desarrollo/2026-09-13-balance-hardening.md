# Balance técnico del hardening — 13 de septiembre de 2026

Este documento consolida lo implementado y comprobado en la rama
`feat/production-readiness`, [PR #22](https://github.com/SciBack/sgc/pull/22).
El código de aplicación verificado llega a `95aa16c`; `7d3dfc8` amplía únicamente
el script de ensayo. Un resultado de CI no acredita despliegue ni aceptación
operativa. La candidata permanece pendiente de autorización de mantenimiento.

## Propósito y arquitectura

El SGC apoya la gestión del área de Calidad: procesos y documentos, evidencias,
indicadores, evaluación, hallazgos, acciones de mejora y verificación. CBC y
acreditación mantienen recorridos y criterios diferentes. La interfaz vigente
es Desk/Workspaces de Frappe; no se creó ni se desplegó una SPA.

Los productores obtienen datos de sistemas fuente o del DW y publican mediciones
trazables. El DW calcula/consolida; el SGC valida, conserva linaje y alimenta
evaluación/alertas. VocBench aporta vocabularios, identificadores y relaciones:
no se usa como motor de cálculo. La conciliación de fórmulas, unidades, códigos,
ámbitos y cortes requiere un catálogo autorizado; no se inventaron mappings.

## Cambios implementados

### Ingesta y lectura de indicadores

- `sgc/ingesta_contrato.py`: contrato v1 estricto, entre 1 y 500 mediciones y hasta
  1 000 000 bytes; números finitos, unidades y versiones explícitas, cortes con
  zona horaria y orden temporal, ámbitos excluyentes y cobertura desconocida
  conservada como tal. Véanse [contrato](ingesta.md) y [OpenAPI](ingesta.openapi.json).
- `sgc/ingesta.py`: autorización por Fuente Dato y cuenta técnica, permisos de
  creación y por documento/ámbito, período abierto y reglas declarativas seguras.
  Identidad estable de lote y medición; repetición idéntica devuelve el resultado
  previo, incluso si posteriormente cerró el período. Un run_id reutilizado con
  contenido distinto se rechaza. No hay commits por fila.
- Lote Ingesta registra aceptación o rechazo de negocio; los rechazos no escriben
  mediciones parciales. Errores inesperados revierten la transacción completa.
  Los cortes anteriores y duplicados heredados impiden una adopción ambigua.
- Los controladores protegen campos administrados, cambios de fuente, escrituras
  en períodos cerrados, renombrados y borrados que eludirían el servicio. La
  adopción conserva nombre e historial de la medición heredada.
- Se ejecutan reglas Rango/Obligatorio; tipos no soportados fallan explícitamente.
  Las advertencias de lotes aceptados generan alertas dentro de la transacción.
- Lectores y reportes prefieren los datos estructurados. Un JSON administrado
  corrupto no se sustituye por prosa heredada; no se infiere una cobertura del 100%.
- La concurrencia real descubrió SQLSTATE 40001 al esperar el bloqueo de fuente.
  Se renueva la transacción con máximo tres intentos, exclusivamente antes de
  cualquier escritura; no se reintenta una transacción parcialmente escrita.

### Productores y contrato de integración

El adaptador DW se desarrolla en un repositorio institucional separado. Conserva
`legacy` como valor predeterminado y ofrece `ingesta-v1` opt-in. Requiere manifiesto
explícito de unidad, versión de fórmula y cortes; congela un lote exclusivo 0600
antes del POST. El reintento manual reutiliza ese contenido sin consultar DW ni
catálogos. No hay reintento automático del POST ni partición silenciosa de lotes.
Una respuesta HTTP 200 con estado Rechazado sigue siendo un fallo de publicación.

Se corrigieron TLS, ceros frente a nulos, cobertura ponderada, denominadores,
grupos incompletos, períodos y colisiones de identidad. Los componentes numéricos
fraccionales se conservan en la ruta estructurada. La unidad del log coincide con
el manifiesto. El motor Oracle heredado falla ante cortes incompatibles; no se
reactivó con equivalencias de períodos inventadas. No se modificaron tablas Oracle
ni el export de tesauro del usuario. El piloto del contrato nuevo sigue pendiente.

### BPMN y editor

- Validación XML del editor: tamaño, namespaces, IDs y referencias; rechazo de
  DTD/ENTITY y contenido ejecutable no permitido. Protección de diagramas
  generados y adjuntos externos antes de modificar archivos.
- Anotaciones visibles basadas en controladores: trazabilidad de Evidencia;
  sincronización aditiva y recálculo de valoraciones; bloqueo tras submit;
  requisitos acumulativos de NC; avance y recálculo del plan al guardar/borrar
  acciones. El XML conserva la función de origen.
- El cierre de Autoevaluación muestra la congelación del marco y registro de
  vigencia dentro del mismo submit, con confirmaciones previas obligatorias.
  No se añadieron pasos humanos inexistentes.
- Las tareas automáticas pasan de cajas de evento a 120×80 px. El generador
  invalida layouts incompatibles y evita que las flechas atraviesen cajas.
  Los quince BPMN se regeneran de manera idempotente y se comprueban en CI.

Se verificó el render de Autoevaluación y NC con el bundle bpmn-js del proyecto,
sin advertencias de importación. Quedan segmentos compartidos/cruces de flechas;
las notas se vinculan por texto/proceso, no por asociaciones gráficas. Esto no
certifica todos los adjuntos institucionales ni la aceptación de sus procedimientos.
Véase [alcance del generador](../diagramas/bpmn/README.md).

### Imagen, respaldos y recuperación

La base Debian bookworm incluía pg_dump 15, incompatible con un servidor PostgreSQL
16. El fallo genérico de backup no demostraba corrupción. El overlay instala
únicamente cliente16 desde PGDG oficial con Signed-By y PATH determinista; verifica
pg_dump, pg_restore y psql. La imagen ARM64 construida seleccionó 16.15 como usuario
frappe y conservó 36 entradas en ambos mappings de assets.

El ensayo `deploy/rehearse_migration.sh` crea PostgreSQL/Redis/sitio efímeros con
recursos limitados, sin puertos ni volúmenes productivos. Comprueba:

1. Upgrade desde la imagen anterior: cinco DocTypes nuevos y medición heredada
   7.25 intacta, sin adopción silenciosa.
2. Backup nativo de Bench con SQL y archivos públicos/privados ficticios no vacíos.
3. Alteración de la medición y eliminación de los archivos antes del restore.
4. Recuperación de 7.25, contenidos exactos y DocTypes nuevos.
5. Restauración del baseline y lectura con la imagen anterior; limpieza efímera.

El ensayo completo `95aa16c-full01` aprobó. También se creó un respaldo online en
el servidor de origen con cliente compatible y se restauró su DB en PostgreSQL
aislado. Rutas, configuración y evidencias institucionales se conservan fuera del
repositorio público. Falta recuperación integral del aplicativo con login/SSO;
el respaldo debe refrescarse con escrituras detenidas durante el mantenimiento.

## Evidencia y commits

| Commit | Resultado |
|---|---|
| `021fa9a` | Primera API atómica e idempotente |
| `fea96e5`, `e314387` | Protección de rutas alternativas, lectores y editor BPMN |
| `c4b069a` | Primer ensayo de migración/rollback aislado |
| `426d4fb`, `7cdf73c` | WSGI concurrente/rollback y corrección de serialización |
| `71d6321` | Controles reales y geometría BPMN |
| `95aa16c` | Cliente PostgreSQL16 en overlay |
| `7d3dfc8` | Ensayo Bench de DB y archivos |

[CI final 34763025218](https://github.com/SciBack/sgc/actions/runs/34763025218)
aprobó. La API quedó además comprobada en
[CI 34761849465](https://github.com/SciBack/sgc/actions/runs/34761849465): 673
integraciones (una omitida), suites adicionales de 22 y 27 y tres pruebas WSGI
reales. Los conteos no deben presentarse como porcentaje de cobertura.
Verificaciones posteriores: 18 pruebas BPMN puras y tres de concordancia; el
adaptador DW aprobó 33 pruebas tanto localmente como en Python3.9 del productor.
Las integraciones Frappe se ejecutaron en CI, no en un bench local.

## Pendientes y orden de continuación

1. Autorización explícita de mantenimiento para migración/reinicio crítico;
   usar la imagen ensayada, respaldo consistente y rollback preparado.
2. Verificar runtime, permisos, login/assets, nuevos DocTypes y logs tras desplegar.
3. Conciliar catálogo y manifiesto real; configurar fuente/cuenta y ejecutar piloto
   antes de activar `ingesta-v1` o cambiar el cron del productor.
4. Completar alcance BPMN y aceptación separada CBC/acreditación por Calidad.
5. Medir carga, cobertura, MFA, retención y SLA; cerrar aceptación operacional.

No se declaró el sistema completamente listo para producción. GitHub, pruebas y
ensayos resueltos no sustituyen estos gates ni la decisión del área de Calidad.
