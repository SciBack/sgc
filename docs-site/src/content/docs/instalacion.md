---
title: Instalación
description: Cómo instalar y operar la app SGC sobre el framework fijado.
---

## Requisitos

- Bench funcional con **Frappe v16.32.0**. La fuente de verdad del tag es
  deploy/frappe.version; no usar la rama móvil version-16.
- PostgreSQL para el site. SGC se valida sobre PostgreSQL, no sobre MariaDB.
- Python 3.14 o posterior y Node 24 para assets y documentación.

## Instalar la app

~~~bash
cd RUTA_DEL_BENCH
bench get-app https://github.com/SciBack/sgc --branch main
bench --site TU_SITE install-app sgc
bench --site TU_SITE migrate
~~~

El hook de migración aplica de forma idempotente los DocTypes, workflows, RBAC,
notificaciones y Workspace SGC.

## Assets y documentación

SGC usa el **Desk nativo de Frappe v16** y el Workspace SGC. Desde la raíz de la app:

~~~bash
python -m compileall -q sgc
bench build --app sgc
cd docs-site && npm ci && npm run build
~~~

## Validar antes de producción

Usa siempre un site aislado y desechable. La suite de integración modifica datos durante
la prueba aunque termine con rollback. No se ejecuta contra el site productivo.

~~~bash
bench --site SITE_DESCARTABLE run-tests --app sgc
~~~

La versión de Frappe, el CI y la biblioteca de referencia se consultan en
[Biblioteca Frappe v16](../referencias/frappe/).

## Construir el overlay Docker

El Dockerfile overlay añade SGC sobre la imagen Frappe base y ejecuta el build de assets.
Antes de cambiar cualquier servicio, identifica la imagen activa y valida el Compose:

~~~bash
docker compose config --images
docker inspect --format '{{.Config.Image}}' CONTENEDOR_BACKEND
docker build --build-arg BASE_IMAGE=IMAGEN_ACTIVA -f deploy/Dockerfile.overlay -t IMAGEN_NUEVA .
docker compose config
~~~

El overlay aborta si el manifiesto de assets queda vacío. Conserva el tag anterior y pide
aprobación antes de recrear servicios críticos.

Después del despliegue, comprobar:

~~~bash
docker compose ps
curl -fsSI https://DOMINIO/desk
curl -fsSI https://DOMINIO/api/method/ping
# Sin sesión, la autorización del manual redirige al login (302). Un 417 significa
# que el `forward_auth` del proxy apunta a un método que ya no existe.
curl -s -o /dev/null -w '%{http_code}\n' https://DOMINIO/api/method/sgc.manual_auth.authorize
~~~

Y comprobar que **la gente puede entrar**, que es lo que ninguna de las órdenes de arriba
pregunta:

~~~bash
bench --site DOMINIO execute sgc.verificacion.run
~~~

Un sitio puede responder 200 en todas sus rutas y ser inservible: el 20-sep-2026 cuatro cuentas
quedaron convertidas en `Website User` al asignarles un rol sin `desk_access`, y estuvieron horas
sin poder trabajar mientras todas las comprobaciones anteriores salían en verde. Esta orden mira
lo que importa —quién puede abrir el Desk— y nombra las cuentas afectadas.

La misma orden avisa si **las tareas programadas han dejado de correr**. Si el scheduler se
para tras un despliegue o un reinicio, no falla nada a la vista: simplemente las evidencias y
los acuerdos vencidos dejan de marcarse como vencidos. El aviso sale cuando una tarea lleva más
de 48 horas sin terminar bien (según el `Scheduled Job Log` de Frappe), cuando está detenida o
cuando el scheduler está desactivado. Además, a los System Manager se les muestra al entrar al
Desk, una vez por sesión, y queda anotado en el Error Log. El umbral se cambia sin tocar código:

~~~bash
bench --site DOMINIO set-config sgc_scheduler_umbral_horas 72
~~~

Y sobre todo responde **qué le falta a la instancia para estar operable**. Una instalación
recién hecha arranca, deja entrar y enseña sus pantallas, pero sin el alta de la institución no
sirve para trabajar. La orden lo separa en tres niveles, y cada hallazgo dice qué hacer:

| Nivel | Qué mira |
|---|---|
| **Bloqueante** | Sin ninguna unidad orgánica; sin periodo académico abierto; matriz de permisos o flujos de aprobación sin aplicar; nadie puede abrir el Desk |
| **Aviso** | Sin inicio de sesión institucional; sin cuenta de correo saliente o con el correo silenciado; sin marcos vigentes o con alguno caducado; identidad neutra; periodo abierto vencido o sin fechas; procesos vigentes sin responsable; tareas programadas paradas |
| **Info** | Árbol de unidades con varias raíces, marcos sin alcance, sin logotipo, correo en ensayo o con lista blanca |

Lo que no da hallazgos sale al final como comprobado. Con algún bloqueante la orden termina
con **código de salida 1**, para encadenarla en un despliegue automatizado. Cada comprobación
se puede correr por separado, por grupo o por nombre (la lista sale si se pide uno que no existe):

~~~bash
bench --site DOMINIO execute sgc.verificacion.run --kwargs "{'solo': 'estructura'}"
bench --site DOMINIO execute sgc.verificacion.run --kwargs "{'solo': 'periodo_vigente,cuenta_saliente'}"
~~~

**Comprobar cada ruta que el proxy sirve, no solo la aplicación.** El manual y el portal
público se sirven por delante de Frappe, así que pueden caerse sin que el sitio principal deje
de responder 200 — que es justo lo que pasó: `/manual` estuvo tres semanas devolviendo 417 sin
que nada lo señalara (issue #67). Lo que lo habría cortado el primer día es esta línea.

## Contribuir

La app usa pre-commit con Ruff, ESLint, Prettier y pyupgrade:

~~~bash
cd apps/sgc
pre-commit install
~~~

Ver [Tests](../desarrollo/tests/) antes de enviar un cambio.
