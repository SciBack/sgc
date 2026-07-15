# SGC — Sistema de Gestión de la Calidad

**SGC** es un producto SciBack: un eQMS (sistema de gestión de la calidad) construido como
app [Frappe](https://frappeframework.com/) v16, pensado para que universidades peruanas
gestionen su proceso de **acreditación** (CONEAU, SINEACE) y sus **Condiciones Básicas de
Calidad (CBC)** ante SUNEDU, con una capa de gestión de procesos alineada a ISO 21001.

Esta documentación cubre la **capa canónica** del producto: el código agnóstico a
cualquier institución. La parametrización específica de un cliente (dominio, branding,
integraciones SSO, credenciales) vive en la capa de esa institución, no aquí.

## Qué resuelve

- **Autoevaluación de acreditación** contra un marco normativo cargable (p. ej. CONEAU
  Programas 2025): el sistema **propone** un nivel de cumplimiento por estándar
  (No Logrado / Logrado / Logrado Plenamente) y el comité **confirma** oficialmente.
- **Diagnóstico de Condiciones Básicas de Calidad (CBC)** exigidas por SUNEDU, con
  semáforo de cumplimiento e informe PDF listo para presentar.
- **Control documental** (ISO 21001 §7.5): ciclo de vida de documentos controlados con
  workflow de aprobación y trazabilidad de versiones.
- **No conformidades y mejora continua (CAPA)**: cadena Hallazgo → No Conformidad →
  Plan de Mejora → Acción de Mejora, con seguimiento de avance y vencimientos.
- **Evidencias**: repositorio de evidencias vinculadas (N:M) a criterios normativos y
  procesos, con expiración de vigencia.
- **Gestión de procesos, riesgos, gobierno y auditoría interna** como módulos de
  soporte del sistema de gestión.

## Cómo está organizado

| Sección | Contenido |
|---|---|
| [Arquitectura](arquitectura.md) | Stack técnico, capas del código, cómo se relacionan backend y frontend |
| [Instalación](instalacion.md) | Cómo instalar la app en un bench Frappe |
| [Módulos](modulos/nucleo.md) | Referencia de DocTypes agrupados por módulo funcional |
| [Manual de uso](manual-uso/autoevaluacion.md) | Flujos operativos paso a paso para el comité de calidad |
| [Desarrollo](desarrollo/rbac.md) | RBAC, tests, arquitectura de la SPA — para quien contribuye código |

## Principio de diseño

El sistema separa siempre **lo que el motor propone** de **lo que el humano confirma**.
Ningún cálculo automático (nivel de estándar, vigencia de acreditación, semáforo CBC)
se escribe como oficial sin una acción humana explícita — ver
[Autoevaluación](manual-uso/autoevaluacion.md) para el caso más representativo de este
principio.
