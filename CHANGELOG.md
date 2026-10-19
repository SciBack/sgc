# Cambios

Qué cambia en cada versión del SGC **para quien lo usa y para quien lo administra**.
El criterio de numeración está en [`docs/desarrollo/versionado.md`](docs/desarrollo/versionado.md).

Cada entrada dice si la versión **requiere migrar** (`bench --site <sitio> migrate`). En este
producto la respuesta casi siempre es sí: Frappe aplica en la migración los permisos, flujos y
avisos que trae la app, y saltársela deja la instancia a medias aunque el sitio responda.

## [Sin publicar]

## [1.7.4] - 2026-10-19

**Requiere migrar:** sí: la migración añade el enlace nuevo al menú Ayuda (Navbar Settings).
Sin cambios de esquema ni de datos.

### Añadido
- **«Manual de usuario» en el menú Ayuda.** Lleva al manual en `/manual/`, en la misma pestaña;
  quien no tenga sesión pasa por el login y vuelve al manual. Una instancia que no publique el
  manual puede ocultarlo con la casilla «Oculto» de Navbar Settings: el migrate no lo vuelve a
  mostrar.

### Corregido
- **El aviso «scheduler-parado» ya no salta en cada actualización.** La comprobación corría con el
  sitio en modo mantenimiento y lo contaba como scheduler apagado. Ahora el mantenimiento no
  cuenta; un sitio que se quede días en mantenimiento sigue avisando por el desfase de las tareas.

## [1.7.3] - 2026-10-16

**Requiere migrar:** sí, como en toda actualización: la migración limpia la caché y el formulario
del hallazgo carga su botón nuevo. Sin cambios de esquema ni de datos.

### Corregido
- **Escalar un hallazgo de auditoría a no conformidad desde la pantalla.** El botón «Escalar a NC»
  del flujo daba error y mandaba a una acción que no existía en pantalla, así que el auditor no
  podía escalar. Ahora crea la no conformidad con los datos del hallazgo y deja los dos enlazados.
- **Escalar un hallazgo de autoevaluación.** La función existía pero no tenía botón. Ahora el
  formulario muestra «Escalar a no conformidad» en debilidades y oportunidades de mejora, solo a
  quien puede crear no conformidades: hasta ahora bastaba con poder leer el hallazgo.

### Cambiado
- **El manual cubre las nueve áreas del menú.** Manuales nuevos de Indicadores, Auditoría, Riesgos
  y Dirección y partes interesadas; Documentos y Mejora continua, reescritos para el usuario (eran
  anteriores a la 1.5.0 y estaban escritos para desarrolladores).
- «Primeros pasos» y «Qué hace cada perfil», al día con la 1.7.2: perfiles decía que la dirección de
  calidad cierra la revisión por la dirección, y la cierra el rectorado.
- Primer tutorial: «Publicar una ficha de caracterización».

## [1.7.2] - 2026-10-15

**Requiere migrar:** no hace falta (la aplicación no cambia; solo el manual).

### Cambiado
- **El manual publicado es solo de usuario.** Se ordena como el menú del SGC: Inicio, Primeros
  pasos, Qué hace cada perfil y un manual por área (Procesos, Documentos, Acreditación y
  licenciamiento, Mejora continua, Configuración). De 89 páginas pasa a 13.
- El manual dice a qué versión corresponde: «Manual del SGC 1.7.2» en el encabezado.
- Las guías de prueba (preparación, recorrido E2E, una por rol, un guion por flujo, regresión) pasan a
  `docs/pruebas/` y la documentación técnica (arquitectura, instalación, alta de institución,
  módulos, RBAC) a `docs/`. Siguen en el repo y la verificación de cobertura sigue vigilándolas.

## [1.7.1] - 2026-10-15

**Requiere migrar:** sí (menú y Elemento Marco). Sin cambios en los datos.

### Añadido
- Menú de Acreditación: **«Condiciones básicas de calidad (CBC)»**, la lista de las condiciones
  del marco de licenciamiento con su unidad responsable. Desde cada condición, «Estructura» en
  Conexiones baja a sus componentes y de ahí a sus indicadores.
- La lista de elementos de un marco muestra la unidad responsable.
- Manual: **«Manual del módulo de Procesos»** (entrar, mapa, crear y editar, procedimientos y BPMN,
  ficha de caracterización, bitácora, portal) y **«Manual de Acreditación y Licenciamiento»**
  (CBC con responsables, preparación del IAC/MIAC, autoevaluación, evidencias). Autoevaluación y
  primeros pasos explican las valoraciones que se crean solas al iniciar.

## [1.7.0] - 2026-10-14

**Requiere migrar:** sí. Campos nuevos en Elemento Marco y un informe nuevo. El marco del IAC se
carga solo en las instancias que lo declaren en `sgc_marcos`.

### Añadido
- Marco **«Ejes Temáticos de Autoevaluación del IAC (MIAC)»** (Sunedu, RS 00105-2026, Tabla 2):
  8 ejes, 21 subejes, 48 pantallas y 12 formatos, para preparar el Informe Anual de Cumplimiento.
  Se declara con `sgc_marcos: ["sunedu-iac-miac-2026"]`.
- Cada elemento de un marco admite **unidad responsable, unidades de apoyo y evidencia requerida**.
- Informe **«Preparación de evidencias»**: por elemento, responsable, evidencias vinculadas y
  validadas y avance por eje.
- El cargador de marcos admite tipo por nodo, marcos de más de 3 niveles, alcance y marcos sin
  escala de valoración.

## [1.6.0] - 2026-10-14

**Requiere migrar:** sí. Pantallas nuevas (Carga de evidencias, informe Implantación del SGC),
campos nuevos en Valoración de criterio y Conexiones en 30 pantallas. Sin cambios en los datos.

### Añadido
- **Carga masiva de evidencias desde un ZIP** (Acreditación y licenciamiento → Carga masiva de
  evidencias). Crea una evidencia por archivo y la vincula al criterio según la carpeta
  (`1.1 Propósitos`, `Criterio 1.1`, `E1`, `I.1`…) o según un `indice.csv`. Omite repetidos,
  tipos no admitidos, rutas con «..» y la basura del sistema; deja en el detalle qué pasó con
  cada archivo. Requiere migrar (pantalla nueva).

## [1.5.0] - 2026-10-14

**Requiere migrar:** sí. Cambia el flujo de aprobación de documentos (acción nueva). Sin cambios en
los datos.

### Cambiado
- Documentos controlados: un documento **publicado u obsoleto ya no se puede modificar encima**
  (título, archivo, código, versión, proceso, firmas). Antes se podía cambiar hasta el archivo de
  un documento vigente sin pasar por revisión ni aprobación (ISO 9001 §7.5.3).
- Acción nueva **«Nueva version»** (Publicado → Borrador) para el dueño del proceso o la DPGC:
  sube la versión, limpia las firmas de la ronda anterior y exige describir el cambio antes de
  enviarlo a revisión. Al publicarse, el cambio queda en el historial del documento.
- El aviso al aprobar sin «Revisado por» dice dónde se rellena.
- No conformidades: con el análisis estructurado (metodología y causas) ya no se exige además el
  texto libre «Análisis de causa raíz»; si falta todo, el aviso dice dónde registrarlo.
- No conformidades: la persona de la DPGC que confirmaba un evento de riesgo (o escalaba un
  hallazgo) nunca podía cerrar la NC que se abría a su nombre. Ahora la regla es la que importa:
  **quien trató la NC (su responsable) no verifica su eficacia**; quien la creó, sí puede.
- **Fichas de caracterización y procedimientos tienen flujo de aprobación** (no lo tenían: su
  estado era libre y el dueño del proceso podía publicar su propia ficha). El dueño elabora y envía
  a revisión; la DPGC aprueba (no quien la creó) y publica; «Nueva version» y «Derogar» como en los
  documentos. Diagramas BPMN 19 y 20 y su página en el manual.
- Autoevaluación: no se puede **consolidar** con criterios sin valorar (se consolidaba con uno
  solo de todo el marco CONEAU). «No aplica» cuenta como valoración.
- Indicadores: el responsable de una ficha recibía el aviso de medir y no podía registrar la
  medición (solo el Data Steward creaba). Ahora la registra el responsable de su ficha; la DPGC,
  la analista y el Data Steward, cualquiera.

## [1.4.1] - 2026-10-14

**Requiere migrar:** sí. Sin cambios en los datos.

### Corregido
- Un documento controlado nuevo no se podía guardar sin escribir a mano un «Código», aunque el
  sistema lo genera solo (PROCESO-SIGLA-NNN). El campo deja de ser obligatorio.
- En los 18 documentos con flujo de aprobación, «Estado» se veía como un desplegable editable:
  elegir otro estado y guardar no hacía nada. Ahora es de solo lectura y explica que se cambia con
  el menú «Acciones».

## [1.4.0] - 2026-10-14

**Requiere migrar:** sí. Las fichas existentes reciben, una vez, lo que el sistema ya sabe de su
proceso (filas nuevas; no se quita nada).

### Cambiado
- La ficha de caracterización recoge sola lo que ya cuelga de su proceso: procedimientos,
  documentos, riesgos y subprocesos. No hay que volver a teclearlo, y nunca se quita lo escrito a
  mano. El proceso enseña además sus riesgos y subprocesos en «Conexiones».
- Una ficha no puede pasar a revisión, aprobarse ni publicarse incompleta: exige objetivo,
  alcance, recursos, responsable del proceso, entradas, salidas, al menos una actividad, un
  indicador y un riesgo (ISO 9001 §4.4.1), y dice qué falta.
- El sistema sella quién la mandó a revisión, quién la aprobó y la fecha de emisión al publicarla.

## [1.3.0] - 2026-10-14

**Requiere migrar:** sí. Sin cambios en los datos ni en los permisos.

### Cambiado
- La página de inicio y las portadas de cada área dejan de ser listas de enlaces (que repetían
  el menú lateral) y enseñan trabajo:
  - **Lo que te toca:** lo que está a tu nombre (no conformidades, acciones, documentos en
    borrador, mediciones pendientes, acuerdos, entregas, riesgos…) con su número, y la lista
    de tus tareas.
  - **Pendientes del área:** lo que espera a alguien (por verificar, por publicar, sin
    responsable, vencido…).
  - **Registrar:** botones para crear lo habitual del área.
  - **Estado del área** (cifras y gráficos) y **Recientes**.
- Todo con bloques nativos de Frappe; el índice de pantallas es el menú lateral.

### Para quien desarrolla
- Política escrita y vigilada en el CI: el SGC se construye con lo que Frappe trae
  (`docs/desarrollo/nativo-frappe.md`, `tests/test_politica_nativa.py`).

## [1.2.2] - 2026-10-14

**Requiere migrar:** sí. Sin cambios en los datos.

### Corregido
- Las cifras y los gráficos de la página de inicio y de las portadas de cada área no salían
  desde la 1.1.0: el sitio dibujaba un hueco en su lugar («Estado del sistema» vacío). Las
  portadas no enlazaban sus cifras y gráficos.

## [1.2.1] - 2026-10-14

**Requiere migrar:** sí (cambia la versión de Frappe). Sin cambios en los datos de calidad ni en
los permisos.

### Cambiado
- Frappe pasa de la 16.51.1 a la **16.52.0**. Trae, entre otras correcciones: el autor de un
  comentario sale de la sesión y no del navegador; ver los conteos por estado de un flujo exige
  permiso sobre el flujo; los filtros «está vacío / no está vacío» sobre números y fechas ya no
  fallan en PostgreSQL; el PDF respeta los saltos de página.
- Es la primera actualización de Frappe con el SGC sobre configuración nativa (1.2.0): solo
  cambia `deploy/frappe.version`.

## [1.2.0] - 2026-10-14

**Requiere migrar:** sí. Sin cambios en los datos de calidad ni en lo que cada persona puede
hacer: los permisos efectivos quedan iguales.

### Cambiado
- Termina el paso a lo nativo de Frappe que empezó la 1.1.0. Lo que antes creaban 29 pasos en
  cada despliegue ahora son documentos estándar de la app, que el `migrate` de Frappe sincroniza:
  - los **permisos** van en cada DocType, en lugar de reescribirse como personalizados;
  - los **roles**, sus perfiles y los **18 flujos de aprobación** (con sus estados y acciones)
    son fixtures;
  - los **20 avisos** y los **5 formatos de impresión** son ficheros estándar de cada módulo.
- Los formatos de impresión leen el nombre y el logotipo de la institución al imprimir, desde
  su `site_config`; cambiar la identidad ya no exige volver a desplegar.
- El despliegue solo ejecuta lo que depende de cada institución: marcos normativos, identidad,
  inicio de sesión institucional y la recolocación de indicadores mal etiquetados por el
  conector externo. Instalar una instancia nueva tarda segundos.

### Para quien administra
- La migración quita los permisos personalizados que coinciden con los estándar. Si una
  institución cambió permisos a mano (Role Permission Manager), se conservan y la migración lo
  avisa.
- Un cambio hecho a mano en un rol, flujo, aviso o formato del SGC se sustituye en la siguiente
  migración por lo que trae la app, como ya pasaba antes.

## [1.1.0] - 2026-10-13

**Requiere migrar:** sí (cambia la versión de Frappe y el Desk pasa a ficheros estándar). Sin
cambios en los datos de calidad.

### Cambiado
- Frappe pasa de la 16.32.0 a la **16.51.1**, que incluye correcciones de seguridad.
- El SGC deja de construirse por encima de Frappe y usa lo que Frappe trae, para que las
  próximas versiones de Frappe se instalen con un `migrate`:
  - Las portadas, los menús de cada área, las cifras y los gráficos vienen como documentos
    estándar de la app, en lugar de crearse con un script en cada despliegue. Lo que una
    institución personalice en ellos se conserva aparte al actualizar.
  - El correo (modo de ensayo, lista blanca, adjuntos de solo consulta) se controla en la cola
    de correo de Frappe, en lugar de sustituir sus clases de avisos.
  - La entrada al Desk va al SGC con el ajuste «App por defecto» de Frappe.

### Corregido
- Con Frappe 16.50 o posterior, los avisos de cambio de estado no salían (ni correo ni
  campana) por un cambio interno de Frappe. Ya no dependen de él.
- La página de inicio de sesión salía en parte en inglés («Sign In», la bienvenida, «Forgot
  password?»): Frappe 16 no trae esos textos en español y ahora los trae el SGC.
- El botón de inicio de sesión institucional mostraba una imagen rota.

## [1.0.0] - 2026-10-13

Primera versión publicada. Recoge todo lo que el producto hace hoy. Las imágenes que se
construyeron antes sin número de versión (julio a octubre de 2026) equivalen, en su conjunto, a
esta versión. No hay un histórico anterior que reconstruir.

**Requiere migrar:** sí. Desde una imagen anterior sin versión, migrar y ejecutar la
verificación de instancia (`bench --site <sitio> execute sgc.verificacion.run`).

### Procesos
- Mapa de procesos en cinco niveles: macroproceso, proceso, subproceso, procedimiento y tarea.
- Ficha de caracterización por proceso (entradas, salidas, interacciones, riesgos, indicadores),
  con historial de cambios e impresión en PDF con la identidad de la institución.
- Procedimientos con su diagrama BPMN, que se edita en el propio Desk.

### Documentos
- Control documental con elaboración, revisión, observaciones selladas, aprobación y publicación.
- Carpetas documentales en árbol, documentos relacionados y documentación externa por enlace.
- «Solo consulta en pantalla»: quien no puede editar un documento lo lee pero no lo descarga, y
  cada consulta queda registrada.
- Tarea de revisión 15 días antes del vencimiento, revisión sin cambios y lista maestra.
- Al publicar, aviso al dueño del proceso y a quien se indique.

### Indicadores
- Ficha de indicador, mediciones por periodo, semáforo y alertas.
- Análisis por periodo, obligatorio si la ficha lo exige.
- Participación de las áreas con pesos.
- Carga de mediciones desde sistemas externos por API, con lotes y reglas de validación.
- Informes por familia y cuadros de mando por área.

### Acreditación y licenciamiento
- Marcos normativos declarables por instancia (`sgc_marcos` en site_config), con su escala y sus
  reglas de vigencia.
- Autoevaluación con valoración por criterio y estándar, trazabilidad a evidencias e informe.
- Cumplimiento de condiciones básicas de calidad con su informe.
- Licenciamiento y acreditación separados: un marco no puede usarse en el flujo del otro.
- Obligaciones con entes externos y sus entregas.

### Mejora continua
- No conformidades con análisis de causas por metodología y causa raíz obligatoria.
- Planes y acciones de mejora con tarea asignada al responsable y difusión del plan aprobado.
- Salidas no conformes (ISO 9001 §8.7), con concesión que no autoriza quien la detectó.
- Cualquier colaborador puede reportar un evento de riesgo; quien reporta no decide.

### Auditoría
- Programa anual de auditoría imprimible y plan de actividades por auditoría.
- Listas de verificación reutilizables y generación de hallazgos sin duplicar.
- Informe de auditoría con aprobación (ISO 19011 §6.5): no aprueba quien lo emitió, y sin informe
  aprobado no se cierra ni el hallazgo ni la auditoría.

### Riesgos
- Matriz de riesgos con evaluación, tratamiento y enlace a procesos y marcos.

### Dirección y partes interesadas
- Política y objetivos de calidad, comités, reuniones y acuerdos.
- Revisión por la dirección con sus entradas y salidas.
- Grupos de interés, instrumentos de consulta y sus resultados.

### Correo y comunicación
- Avisos por correo y en la campana del Desk en cada transición real de estado.
- Modo de ensayo y lista blanca: una instancia nueva nace sin escribir a nadie.
- Envío a demanda de documentos y fichas publicados, también a destinatarios externos.
- Comunicados a roles para novedades y mantenimientos programados, con 24 h de antelación.

### Acceso y seguridad
- Matriz de permisos por rol aplicada y reconciliada en cada migración.
- Inicio de sesión institucional (OIDC) declarado en site_config.
- Contraseñas con longitud y clases de caracteres mínimas.
- Quien ejecuta un control lo sella el sistema, no el formulario.

### Administración de la instancia
- Alta de una institución con un solo comando y un perfil: identidad, marcos, estructura y SSO.
- Importador de la estructura institucional desde CSV o Excel, que carga todo o nada.
- Verificación de instancia: dice qué falta para estar operable y quién no puede entrar.
- Estado de la instancia para soporte (`/api/method/sgc.estado.instancia`, solo System Manager):
  versión, último migrate y si quedó uno pendiente, scheduler, correo y SSO. No devuelve datos
  de negocio ni de personas.
- Aviso a los administradores si las tareas programadas dejan de correr.
- «Ayuda → Reportar un problema» hacia el helpdesk de la institución.
- Identidad institucional (nombre, logo, membrete) en site_config, fuera del código.

### Publicación y actualización
- Imagen publicada por el CI para cada versión (`ghcr.io/sciback/sgc-frappe:<versión>`, ARM64),
  construida desde cero y con su procedencia (versión, commit, Frappe) en las etiquetas. Antes
  de publicarse, pasa la suite completa y una prueba de humo sobre un sitio nuevo.
- Actualización de una instancia con un solo comando (`deploy/actualizar.sh`): exige el aviso
  previo a los usuarios, respalda, pone el sitio en mantenimiento, migra y se comprueba sola. Si
  la comprobación no pasa, el sitio se queda en mantenimiento y el script dice cómo volver atrás.
- Página de mantenimiento mientras se recrean los servicios, en lugar de un error de conexión.
