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
      { label: 'Autoevaluación', doctype: 'Autoevaluacion', icon: 'lucide-clipboard-check' },
      { label: 'Valoración Estándar', doctype: 'Valoracion Estandar', icon: 'lucide-badge-check' },
      { label: 'Valoración Criterio', doctype: 'Valoracion Criterio', icon: 'lucide-list-checks' },
      { label: 'Evidencia', doctype: 'Evidencia', icon: 'lucide-paperclip' },
    ],
  },
  {
    label: 'Marcos e indicadores',
    icon: 'lucide-list-checks',
    items: [
      { label: 'Marco Normativo', doctype: 'Marco Normativo', icon: 'lucide-book-open-check' },
      { label: 'Elemento Marco', doctype: 'Elemento Marco', icon: 'lucide-layers-3' },
      { label: 'Indicador', doctype: 'Indicador', icon: 'lucide-chart-no-axes-column-increasing' },
      { label: 'Ficha Indicador', doctype: 'Ficha Indicador', icon: 'lucide-file-chart-column' },
      { label: 'Escala Valoración', doctype: 'Escala Valoracion', icon: 'lucide-ruler' },
    ],
  },
  {
    label: 'Mejora continua',
    icon: 'lucide-trending-up',
    items: [
      { label: 'Hallazgo', doctype: 'Hallazgo', icon: 'lucide-search-check' },
      { label: 'No Conformidad', doctype: 'No Conformidad', icon: 'lucide-circle-alert' },
      { label: 'Plan Mejora', doctype: 'Plan Mejora', icon: 'lucide-list-todo' },
      { label: 'Acción Mejora', doctype: 'Accion Mejora', icon: 'lucide-circle-check-big' },
    ],
  },
  {
    label: 'Gestión documental',
    icon: 'lucide-file-text',
    items: [
      { label: 'Documento Controlado', doctype: 'Documento Controlado', icon: 'lucide-file-check-2' },
      { label: 'Trazabilidad', doctype: 'Trazabilidad', icon: 'lucide-git-fork' },
    ],
  },
  {
    label: 'Procesos',
    icon: 'lucide-workflow',
    items: [
      { label: 'Proceso', doctype: 'Proceso', icon: 'lucide-workflow' },
      { label: 'Procedimiento', doctype: 'Procedimiento', icon: 'lucide-list-ordered' },
      { label: 'Ficha Caracterización Proceso', doctype: 'Ficha Caracterizacion Proceso', icon: 'lucide-file-cog' },
    ],
  },
  {
    label: 'Gobierno de la calidad',
    icon: 'lucide-users',
    items: [
      { label: 'Comité', doctype: 'Comite', icon: 'lucide-users-round' },
      { label: 'Política Calidad', doctype: 'Politica Calidad', icon: 'lucide-scroll-text' },
      { label: 'Objetivo Calidad', doctype: 'Objetivo Calidad', icon: 'lucide-target' },
      { label: 'Reunión', doctype: 'Reunion', icon: 'lucide-calendar-days' },
    ],
  },
  {
    label: 'Encuestas y grupos de interés',
    icon: 'lucide-clipboard-list',
    items: [
      { label: 'Grupo de Interés', doctype: 'Grupo Interes', icon: 'lucide-contact-round' },
      { label: 'Instrumento', doctype: 'Instrumento', icon: 'lucide-clipboard-list' },
      { label: 'Aplicación Instrumento', doctype: 'Aplicacion Instrumento', icon: 'lucide-send' },
    ],
  },
  {
    label: 'Riesgos y obligaciones',
    icon: 'lucide-shield-alert',
    items: [
      { label: 'Riesgo', doctype: 'Riesgo', icon: 'lucide-triangle-alert' },
      { label: 'Matriz Riesgo', doctype: 'Matriz Riesgo', icon: 'lucide-table-properties' },
      { label: 'Evaluación Riesgo', doctype: 'Evaluacion Riesgo', icon: 'lucide-clipboard-check' },
      { label: 'Tratamiento Riesgo', doctype: 'Tratamiento Riesgo', icon: 'lucide-shield-check' },
      { label: 'Obligación Ente', doctype: 'Obligacion Ente', icon: 'lucide-scale' },
    ],
  },
  {
    label: 'Auditoría',
    icon: 'lucide-clipboard-check',
    items: [
      { label: 'Programa Auditoría', doctype: 'Programa Auditoria', icon: 'lucide-calendar-check-2' },
      { label: 'Auditoría', doctype: 'Auditoria', icon: 'lucide-scan-search' },
      { label: 'Informe Auditoría', doctype: 'Informe Auditoria', icon: 'lucide-file-search' },
      { label: 'Hallazgo Auditoría', doctype: 'Hallazgo Auditoria', icon: 'lucide-file-warning' },
      { label: 'Revisión Dirección', doctype: 'Revision Direccion', icon: 'lucide-user-round-check' },
    ],
  },
  {
    label: 'Estructura institucional',
    icon: 'lucide-building-2',
    items: [
      { label: 'Programa', doctype: 'Programa', icon: 'lucide-graduation-cap' },
      { label: 'Unidad Orgánica', doctype: 'Unidad Organica', icon: 'lucide-building-2' },
      { label: 'Período Académico', doctype: 'Periodo Academico', icon: 'lucide-calendar-range' },
      { label: 'Programa Sede', doctype: 'Programa Sede', icon: 'lucide-map-pinned' },
    ],
  },
]
