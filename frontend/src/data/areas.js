// Áreas del menú lateral — mismo contenido que scripts/frappe/sgc_menu_apply.py
// (que puebla el sidebar nativo de Frappe). Aquí es la fuente para el
// SidebarMenu de la SPA. Mantener ambas listas sincronizadas si cambian los
// DocTypes; a mediano plazo esto se puede derivar de la API en vez de estar
// hardcodeado.
export const AREAS = [
  {
    label: 'Acreditación',
    icon: 'lucide-award',
    items: [
      { label: 'Autoevaluación', doctype: 'Autoevaluacion' },
      { label: 'Valoración Estándar', doctype: 'Valoracion Estandar' },
      { label: 'Valoración Criterio', doctype: 'Valoracion Criterio' },
      { label: 'Evidencia', doctype: 'Evidencia' },
    ],
  },
  {
    label: 'Marcos e indicadores',
    icon: 'lucide-list-checks',
    items: [
      { label: 'Marco Normativo', doctype: 'Marco Normativo' },
      { label: 'Elemento Marco', doctype: 'Elemento Marco' },
      { label: 'Indicador', doctype: 'Indicador' },
      { label: 'Ficha Indicador', doctype: 'Ficha Indicador' },
      { label: 'Escala Valoración', doctype: 'Escala Valoracion' },
    ],
  },
  {
    label: 'Mejora continua',
    icon: 'lucide-trending-up',
    items: [
      { label: 'Hallazgo', doctype: 'Hallazgo' },
      { label: 'No Conformidad', doctype: 'No Conformidad' },
      { label: 'Plan Mejora', doctype: 'Plan Mejora' },
      { label: 'Acción Mejora', doctype: 'Accion Mejora' },
    ],
  },
  {
    label: 'Gestión documental',
    icon: 'lucide-file-text',
    items: [
      { label: 'Documento Controlado', doctype: 'Documento Controlado' },
      { label: 'Trazabilidad', doctype: 'Trazabilidad' },
    ],
  },
  {
    label: 'Procesos',
    icon: 'lucide-workflow',
    items: [
      { label: 'Proceso', doctype: 'Proceso' },
      { label: 'Procedimiento', doctype: 'Procedimiento' },
      { label: 'Ficha Caracterización Proceso', doctype: 'Ficha Caracterizacion Proceso' },
    ],
  },
  {
    label: 'Gobierno de la calidad',
    icon: 'lucide-users',
    items: [
      { label: 'Comité', doctype: 'Comite' },
      { label: 'Política Calidad', doctype: 'Politica Calidad' },
      { label: 'Objetivo Calidad', doctype: 'Objetivo Calidad' },
      { label: 'Reunión', doctype: 'Reunion' },
    ],
  },
  {
    label: 'Encuestas y grupos de interés',
    icon: 'lucide-clipboard-list',
    items: [
      { label: 'Grupo de Interés', doctype: 'Grupo Interes' },
      { label: 'Instrumento', doctype: 'Instrumento' },
      { label: 'Aplicación Instrumento', doctype: 'Aplicacion Instrumento' },
    ],
  },
  {
    label: 'Riesgos y obligaciones',
    icon: 'lucide-shield-alert',
    items: [
      { label: 'Riesgo', doctype: 'Riesgo' },
      { label: 'Matriz Riesgo', doctype: 'Matriz Riesgo' },
      { label: 'Evaluación Riesgo', doctype: 'Evaluacion Riesgo' },
      { label: 'Tratamiento Riesgo', doctype: 'Tratamiento Riesgo' },
      { label: 'Obligación Ente', doctype: 'Obligacion Ente' },
    ],
  },
  {
    label: 'Auditoría',
    icon: 'lucide-clipboard-check',
    items: [
      { label: 'Programa Auditoría', doctype: 'Programa Auditoria' },
      { label: 'Auditoría', doctype: 'Auditoria' },
      { label: 'Informe Auditoría', doctype: 'Informe Auditoria' },
      { label: 'Hallazgo Auditoría', doctype: 'Hallazgo Auditoria' },
      { label: 'Revisión Dirección', doctype: 'Revision Direccion' },
    ],
  },
  {
    label: 'Estructura institucional',
    icon: 'lucide-building-2',
    items: [
      { label: 'Programa', doctype: 'Programa' },
      { label: 'Unidad Orgánica', doctype: 'Unidad Organica' },
      { label: 'Período Académico', doctype: 'Periodo Academico' },
      { label: 'Programa Sede', doctype: 'Programa Sede' },
    ],
  },
]
