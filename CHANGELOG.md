# Cambios

Qué cambia en cada versión del SGC **para quien lo usa y para quien lo administra**.
El criterio de numeración está en [`docs/desarrollo/versionado.md`](docs/desarrollo/versionado.md).

Cada entrada dice si la versión **requiere migrar** (`bench --site <sitio> migrate`). En este
producto la respuesta casi siempre es sí: el despliegue aplica permisos, flujos y avisos en cada
migración, y saltársela deja la instancia a medias aunque el sitio responda.

## [Sin publicar]

### Corregido
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
