# Herramientas para BPMN: qué se evaluó y qué se decidió

Evaluación hecha el **2026-08-09**. Todos los datos de estrellas, licencias y fechas de
actividad se verificaron ese día contra las fuentes; conviene revalidarlos antes de
tomar la decisión otra vez.

## La pregunta

El área de calidad trabaja con BPMN, que es la notación de la gestión por procesos. El
sistema tiene 14 workflows implementados y ninguno documentado en esa notación. ¿Con qué
se genera, se visualiza y se edita BPMN, sin pagar licencias y de forma que el equipo
técnico pueda automatizarlo?

## Decisión

1. **Generar** el `.bpmn` desde las definiciones de workflow: **Python y XML, sin dependencias.**
2. **Visualizar y editar en línea**: **bpmn-js** (variante Modeler), dentro de la SPA del
   sistema, que ya usa Vue 3, `frappe-ui` y Tailwind.
3. **Validar**: contra el XSD oficial de la OMG, en el pipeline.
4. **Editar los workflows reales** (los que gobiernan el motor): **el Workflow Builder
   nativo del framework**, que ya viene instalado. No se construye nada para eso.

El punto 4 es el que ahorra más trabajo: la edición visual que cambia el sistema **ya
existe**. Lo que no existe es BPMN, y BPMN no sirve para gobernar el motor: sirve para
hablar con el área de calidad y con sus herramientas.

## Lo evaluado

| Herramienta | Estrellas | Licencia | Actividad | Veredicto |
|---|---|---|---|---|
| **bpmn-js** | 9 627 | bpmn.io (gratis, comercial incluido, **watermark obligatorio**) | activa | **Elegida.** BPMN 2.0 nativo, funciona en el navegador sin servidor, importa y exporta XML |
| LogicFlow | 11 627 | Apache-2.0 | activa | Descartada. Más estrellas y mejor licencia, pero **BPMN no es su formato nativo**: su modelo propio es JSON y BPMN aparece como conversión hacia otros motores |
| Camunda 7 CE | 4 269 | Apache-2.0 | **fin de vida** | Descartada. Sin releases ni parches de seguridad para Community tras 7.24 (oct-2025) |
| Camunda 8 | — | Camunda License v1 (**source-available**, no libre) | activa | Descartada. **Exige licencia de producción** desde 8.6 |
| Flowable | 9 449 | Apache-2.0 | activa | Descartada para este uso. Es un motor de ejecución en Java; el sistema ya tiene motor |
| Bizagi Modeler | — | propietario (gratuito para modelar) | activa | No se adopta como herramienta del proyecto, pero **es un cliente válido**: abre el `.bpmn` estándar que generemos. Es de escritorio, así que no se puede automatizar |
| camunda-modeler | 1 697 | **MIT** | activa | **Alternativa libre a Bizagi** para quien prefiera escritorio. Construida sobre bpmn.io |
| SpiffWorkflow | 1 910 | LGPL-3.0 | activa | No se adopta hoy. **Anotada**: es un motor BPMN en **Python puro**, el único candidato coherente con este stack si algún día hiciera falta ejecutar BPMN |
| HazelNode | 19 | **AGPL-3.0** | último push ene-2026 | Descartada. Ver abajo |
| Kroki | 4 276 | MIT | activa | Sin evaluar. Renderiza diagramas desde texto; habría que comprobar su soporte de BPMN |

## Sobre HazelNode

Apareció citada en la discusión de "no-code workflows" del framework. Es automatización
de workflows para el ecosistema Frappe, no una herramienta BPMN.

Se descarta por tres razones, en orden de peso:

1. **No resuelve el problema.** No menciona BPMN por ningún lado. Va de disparadores y
   acciones, que es otra necesidad.
2. **AGPL-3.0.** Es copyleft fuerte y alcanza al software ofrecido como servicio en red.
   Integrarla en un producto que se despliega para terceros obliga a mirar con lupa la
   compatibilidad de licencias, y este producto **hoy no declara ninguna** (ver abajo).
3. **Adopción y mantenimiento mínimos.** 19 estrellas y sin movimiento desde enero de
   2026. Para una pieza que quedaría en el camino crítico de la gestión de procesos, es
   poco respaldo.

No es un juicio sobre su calidad: es que no resuelve esto y su licencia obliga a un
análisis que no toca hacer por una herramienta que no necesitamos.

## Lo que el framework no va a darnos

- **No existe ninguna referencia a BPMN** en el framework (verificado sobre la versión
  16.29 instalada).
- El **Workflow Builder** nativo usa `@vue-flow/core` sobre el modelo de estados propio
  del framework: edita workflows de verdad, pero **no importa ni exporta BPMN**.
- La discusión de la comunidad más cercana a esto (`frappe/frappe#21191`, "feat: no-code
  workflows") estuvo **tres años abierta y se cerró sin implementación** el 2026-07-05.
  En sus comentarios, un contribuidor de SpiffWorkflow se ofreció a resolverlo con BPMN y
  swimlanes; no prosperó.

Conclusión: si se quiere BPMN, se construye. No va a llegar de fábrica.

## Riesgo abierto, pendiente de medir

Los metadatos propios (qué rol ejecuta cada transición, si permite autoaprobación) no son
BPMN estándar y viajan en `extensionElements`. **No está comprobado que las herramientas
de terceros los conserven al guardar.** Se mide generando un fichero, abriéndolo en la
herramienta del área de calidad, guardándolo y comparando qué sobrevive. Es lo único que
podría obligar a rediseñar el formato de salida.

## Hallazgo lateral: este repositorio no declara licencia

Al revisar la AGPL de HazelNode se comprobó que **este repositorio no tiene fichero
`LICENSE` ni declara licencia en `pyproject.toml`**, siendo público.

Sin licencia explícita, por defecto se reservan todos los derechos: nadie puede
legalmente reutilizarlo, redistribuirlo ni contribuir, aunque el código esté a la vista.
Para un producto pensado para desplegarse en varias instituciones, conviene resolverlo.
No es parte de esta decisión, pero se deja anotado porque salió aquí.
