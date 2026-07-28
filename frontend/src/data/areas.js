// Áreas del menú lateral — mismo contenido que scripts/frappe/sgc_menu_apply.py
// (que puebla el sidebar nativo de Frappe). Aquí es la fuente para el
// SidebarMenu de la SPA. Mantener ambas listas sincronizadas si cambian los
// DocTypes; a mediano plazo esto se puede derivar de la API en vez de estar
// hardcodeado.

// Los iconos son COMPONENTES, no cadenas: el estilo SciBack §3 exige que un prop
// de icono nunca se tipe como string — tiparlo así obliga a pasar emoji y bloquea
// el icono de trazo. Pack de la casa: reicon (build Vue).
import {
  AlertCircle,
  AlertTriangle,
  ArchiveBook,
  Award,
  Bank,
  Book,
  BranchDown,
  Building,
  Calendar,
  CalendarCheck,
  CalendarDays,
  CardSearch,
  ChartBar,
  ChartLine,
  ChartSquare,
  CheckCircle,
  CheckListNotes,
  CheckListSquare,
  ClipboardCheck,
  ClipboardList,
  ClipboardText,
  CodeScan,
  DocText,
  DocumentText,
  Eye,
  FileCheck,
  FileContent,
  FileError,
  FileText,
  Flag,
  GraduationCap,
  Grid,
  Hierarchy,
  Judge,
  Layers,
  List3,
  Location,
  Nodes,
  Office,
  Paperclip,
  Ruler,
  Send,
  ShieldAlert,
  ShieldCheck,
  Target,
  UserCheck,
  UserId,
  Users,
  Verified
} from 'reicon-vue'

export const AREAS = [
  {
    label: 'Acreditación',
    icon: Award,
    items: [
      { label: 'Autoevaluación', doctype: 'Autoevaluacion', icon: ClipboardCheck },
      { label: 'Valoración Estándar', doctype: 'Valoracion Estandar', icon: Verified },
      { label: 'Valoración Criterio', doctype: 'Valoracion Criterio', icon: CheckListSquare },
      { label: 'Evidencia', doctype: 'Evidencia', icon: Paperclip },
    ],
  },
  {
    label: 'Marcos e indicadores',
    icon: ArchiveBook,
    items: [
      { label: 'Marco Normativo', doctype: 'Marco Normativo', icon: Book },
      { label: 'Elemento Marco', doctype: 'Elemento Marco', icon: Layers },
      { label: 'Indicador', doctype: 'Indicador', icon: ChartBar },
      { label: 'Ficha Indicador', doctype: 'Ficha Indicador', icon: FileText },
      { label: 'Escala Valoración', doctype: 'Escala Valoracion', icon: Ruler },
    ],
  },
  {
    label: 'Mejora continua',
    icon: ChartLine,
    items: [
      { label: 'Hallazgo', doctype: 'Hallazgo', icon: Flag },
      { label: 'No Conformidad', doctype: 'No Conformidad', icon: AlertCircle },
      { label: 'Plan Mejora', doctype: 'Plan Mejora', icon: CheckListNotes },
      { label: 'Acción Mejora', doctype: 'Accion Mejora', icon: CheckCircle },
    ],
  },
  {
    label: 'Gestión documental',
    icon: DocText,
    items: [
      { label: 'Documento Controlado', doctype: 'Documento Controlado', icon: FileCheck },
      { label: 'Trazabilidad', doctype: 'Trazabilidad', icon: BranchDown },
    ],
  },
  {
    label: 'Procesos',
    icon: Nodes,
    items: [
      { label: 'Proceso', doctype: 'Proceso', icon: Hierarchy },
      { label: 'Procedimiento', doctype: 'Procedimiento', icon: List3 },
      { label: 'Ficha Caracterización Proceso', doctype: 'Ficha Caracterizacion Proceso', icon: FileContent },
    ],
  },
  {
    label: 'Gobierno de la calidad',
    icon: Bank,
    items: [
      { label: 'Comité', doctype: 'Comite', icon: Users },
      { label: 'Política Calidad', doctype: 'Politica Calidad', icon: DocumentText },
      { label: 'Objetivo Calidad', doctype: 'Objetivo Calidad', icon: Target },
      { label: 'Reunión', doctype: 'Reunion', icon: CalendarDays },
    ],
  },
  {
    label: 'Encuestas y grupos de interés',
    icon: ClipboardList,
    items: [
      { label: 'Grupo de Interés', doctype: 'Grupo Interes', icon: UserId },
      { label: 'Instrumento', doctype: 'Instrumento', icon: ClipboardText },
      { label: 'Aplicación Instrumento', doctype: 'Aplicacion Instrumento', icon: Send },
    ],
  },
  {
    label: 'Riesgos y obligaciones',
    icon: ShieldAlert,
    items: [
      { label: 'Riesgo', doctype: 'Riesgo', icon: AlertTriangle },
      { label: 'Matriz Riesgo', doctype: 'Matriz Riesgo', icon: Grid },
      { label: 'Evaluación Riesgo', doctype: 'Evaluacion Riesgo', icon: ChartSquare },
      { label: 'Tratamiento Riesgo', doctype: 'Tratamiento Riesgo', icon: ShieldCheck },
      { label: 'Obligación Ente', doctype: 'Obligacion Ente', icon: Judge },
    ],
  },
  {
    label: 'Auditoría',
    icon: Eye,
    items: [
      { label: 'Programa Auditoría', doctype: 'Programa Auditoria', icon: CalendarCheck },
      { label: 'Auditoría', doctype: 'Auditoria', icon: CodeScan },
      { label: 'Informe Auditoría', doctype: 'Informe Auditoria', icon: CardSearch },
      { label: 'Hallazgo Auditoría', doctype: 'Hallazgo Auditoria', icon: FileError },
      { label: 'Revisión Dirección', doctype: 'Revision Direccion', icon: UserCheck },
    ],
  },
  {
    label: 'Estructura institucional',
    icon: Building,
    items: [
      { label: 'Programa', doctype: 'Programa', icon: GraduationCap },
      { label: 'Unidad Orgánica', doctype: 'Unidad Organica', icon: Office },
      { label: 'Período Académico', doctype: 'Periodo Academico', icon: Calendar },
      { label: 'Programa Sede', doctype: 'Programa Sede', icon: Location },
    ],
  },
]
