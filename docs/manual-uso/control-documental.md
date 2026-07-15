# Manual de uso · Control documental

Implementa ISO 21001 §7.5 (información documentada) sobre el DocType **Documento
Controlado**.

## Ciclo de vida de un documento

1. **Crear**: al guardar por primera vez, el sistema genera el código
   `[PROCESO]-[SIGLA]-[NNN]` automáticamente (el correlativo es único por prefijo, no
   se reutiliza aunque se borre un documento intermedio).
2. **Adjuntar el archivo**: es obligatorio — el sistema bloquea el guardado sin un
   archivo adjunto (campo `archivo`, tipo Attach).
3. **Versionar**: cada nueva versión exige una `descripcion_cambio` (obligatoria, no
   se puede versionar en silencio). Queda registrada en la tabla hija
   `historial_cambios` (`Cambio Documento`).
4. **Workflow de aprobación**: el documento pasa por los estados definidos en el
   workflow nativo `Dueño de Proceso → DPGC → Autoridad Aprobadora`. Los saltos de
   estado inválidos están bloqueados (no se puede pasar de Borrador a Publicado sin
   pasar por revisión).
5. **Publicar**: al publicarse, el sistema fija automáticamente la fecha de próxima
   revisión anual y, si el documento reemplaza a otro (`reemplaza_a`), marca ese
   documento anterior como obsoleto.

## Tipos de documento

El campo `tipo_documento` clasifica el documento (política, procedimiento, formato,
registro, etc.) — se usa para la Lista Maestra (ver abajo).

## Vincular el documento a un proceso

Un Documento Controlado se asocia a un `Proceso` vía **Doc Proceso Link** (módulo
Procesos) — así el mapa de procesos puede mostrar qué documentos soportan cada
proceso.

## Exportar la Lista Maestra

`lista_maestra.exportar_lista_maestra(estado=None, proceso=None)` genera un Excel
(8 columnas en español) con todos los documentos controlados, filtrable por estado o
proceso — el entregable típico que un auditor externo pide para verificar el control
documental.
