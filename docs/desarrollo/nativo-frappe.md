# Política: el SGC se construye con lo que Frappe trae

**Regla:** toda la configuración y la interfaz del SGC usa los mecanismos nativos de Frappe.
Nada construido por encima que haya que rehacer cuando sale una versión nueva de Frappe.

**Por qué.** Al subir de Frappe 16.32 a 16.51 fallaron 19 pruebas: el SGC sobrescribía una
clase de Frappe y creaba menús con un script, y Frappe había cambiado las dos cosas por
dentro. Desde la 1.2.0 la configuración es nativa, y la 16.52 entró cambiando una línea
(`deploy/frappe.version`): del cambio a producción, una hora.

## Qué es nativo

| Qué | Cómo |
|---|---|
| Pantallas y campos | DocType en su módulo (`sgc/<módulo>/doctype/`) |
| Permisos | El `permissions` del DocType. Nada de Custom DocPerm escritos por código |
| Roles, perfiles, flujos de aprobación | Fixtures (`sgc/fixtures/`, hook `fixtures`) |
| Avisos | Notification estándar en `sgc/<módulo>/notification/`, mensaje en `.html` (`message_type: HTML`) |
| Formatos de impresión | Print Format estándar; la identidad se lee al imprimir (`sgc_identidad()`) |
| Portadas, menús, cifras, gráficos | Workspace, Sidebar, Number Card y Dashboard Chart estándar en su módulo |
| Filtros guardados de una lista | List Filter estándar (`is_standard: 1`) en `sgc/<módulo>/doctype/<doctype>/list_filter/<nombre>.json` |
| Ajustes sobre DocTypes de Frappe | Property Setter / Custom Field en `sgc/<módulo>/custom/<doctype>.json` |
| Reaccionar a algo | `doc_events`, `scheduler_events`, controladores del propio DocType |
| Arreglos de datos de una vez | `patches.txt` (ojo: en un sitio nuevo no corren) |

Las portadas solo usan bloques nativos de Workspace: `header`, `paragraph`, `shortcut` (con
`stats_filter`, que admite `frappe.session.user` para «lo mío»), `quick_list`, `number_card`,
`chart`, `card` y `spacer`. **No** `custom_block`: es HTML y JS propios metidos en la portada.

**Al cambiar un fichero estándar, sube su `modified`.** El `migrate` solo reimporta una portada,
un menú, una guía, una cifra o un gráfico si el `modified` del fichero es posterior al de la base;
si no, lo salta en silencio. Pasó en la 1.7.13: los DocTypes y los filtros nuevos entraron, pero
6 portadas y 3 menús siguieron como antes en producción, con el filtro que contaba fichas sin fecha
incluido. Se arregló en la 1.7.14 subiendo la fecha.

## Qué no se hace

- Sobrescribir clases de Frappe (`override_doctype_class`) ni sus métodos de API
  (`override_whitelisted_methods`).
- Parchear el JavaScript del Desk o cargar JS/CSS global para cambiar cómo se ve Frappe.
- Crear o reescribir configuración con un script en cada `migrate` (`after_migrate`). El
  orquestador `sgc/setup/f_deploy_run_all.py` queda solo para lo que depende de cada
  institución y sale de su `site_config`.

Si algo no se puede hacer con lo nativo, se discute antes y se anota abajo como deuda con su
motivo. Lo que no está en la lista no entra.

## Deuda conocida (se reduce, no crece)

| Qué | Por qué existe |
|---|---|
| `override_doctype_class`: `File` → `FicheroSGC` | «Solo consulta en pantalla»: cerrar la descarga por URL directa |
| `override_whitelisted_methods`: `zip_files` | La misma regla para la descarga en lote |
| `override_whitelisted_methods`: `update_password`, `test_password_strength` | Exigencia de clases de caracteres en la contraseña (B4) |
| `app_include_js`: `latido_scheduler.js`, `soporte.js` | Aviso de scheduler parado y menú «Reportar un problema» |

## Cómo se vigila

`tests/test_politica_nativa.py` (en el CI, sin Frappe) falla si:

- aparece una sobrescritura, un JS global o un `after_migrate` fuera de la lista de arriba;
- el código de la app (fuera de pruebas y parches) crea Workspace, Workflow, Notification,
  Print Format, Role, Custom DocPerm, Number Card, Dashboard Chart, Sidebar, Custom Field,
  Property Setter o List Filter;
- una portada usa un bloque que no es nativo.

Ampliar la deuda exige cambiar esa prueba y este documento en el mismo PR, con el motivo.
