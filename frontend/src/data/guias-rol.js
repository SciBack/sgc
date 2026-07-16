// Mini-manual en contexto: por cada rol, los pasos exactos que hace en el
// sistema, de principio a fin. Se muestra en Inicio ("Guía rápida por rol") para
// que una persona nueva sepa qué hacer sin salir de la app. El detalle completo
// (todos los estados) vive en el manual: manual-uso/primeros-pasos.
export const GUIAS_ROL = [
  {
    rol: 'Responsable de Calidad de Programa',
    corto: 'Comité del programa',
    resumen: 'Llevas la autoevaluación de tu programa de principio a fin.',
    pasos: [
      'En Inicio, abre tu autoevaluación (o créala en Acreditación → Autoevaluación → Nueva).',
      'Pulsa «Iniciar evaluación».',
      'Por cada criterio: sube su evidencia, vincúlala al criterio y valóralo.',
      'Confirma los niveles y pulsa «Enviar a revisión».',
    ],
    fin: 'Tu parte termina al enviar a revisión: la DPGC consolida y cierra.',
  },
  {
    rol: 'DPGC',
    corto: 'Dirección de calidad',
    resumen: 'No ejecutas la valoración: la revisas, apruebas y cierras.',
    pasos: [
      'Revisa el panel «Requiere atención» de Inicio.',
      'Consolida o devuelve las autoevaluaciones que te enviaron.',
      'Verifica y cierra las no conformidades y los planes de mejora.',
      'Aprueba y publica los documentos que llegan a revisión.',
    ],
    fin: 'Tu parte cierra cada expediente (consolidar / cerrar).',
  },
  {
    rol: 'Dueño de Proceso',
    corto: 'Control documental',
    resumen: 'Mantienes los documentos de tu proceso.',
    pasos: [
      'Ve a Gestión documental → Documento Controlado → Nuevo.',
      'Redacta el documento y adjunta el archivo (PDF).',
      'Pulsa «Enviar a revisión».',
      'Si lo observan, corrígelo y vuelve a enviarlo.',
    ],
    fin: 'La DPGC lo aprueba y la autoridad lo publica.',
  },
  {
    rol: 'Auditor Interno',
    corto: 'Aseguramiento',
    resumen: 'Constatas: no ejecutas ni cierras.',
    pasos: [
      'Entra al área de Auditoría.',
      'Registra tus hallazgos de auditoría.',
    ],
    fin: 'El tratamiento y el cierre son de otros roles.',
  },
]
