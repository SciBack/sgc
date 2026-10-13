---
title: Alta de una institución
description: "Runbook: de un sitio recién creado a una instancia operable con un solo comando y un perfil."
---

Este procedimiento deja operable una instancia del SGC para una institución nueva. Lo puede
seguir alguien que no escribió el código: cada paso dice qué hacer, qué tiene que salir y qué
hacer si no sale.

**Empieza donde termina el despliegue.** El alta no crea el sitio, no pide certificados, no
registra el cliente en el proveedor de identidad y no configura el correo: todo eso es
infraestructura y depende de terceros. Hay que tenerlo hecho antes.

## 0. Lo que tiene que estar hecho antes

| Qué | Cómo se comprueba |
|---|---|
| El sitio existe y tiene la app instalada ([Instalación](../instalacion/)) | `bench --site SITIO list-apps` muestra `sgc` |
| Si va a haber inicio de sesión institucional: el cliente OIDC registrado en el proveedor | El administrador del proveedor entrega `issuer`, `client_id` y el secreto por un canal de secretos |
| El logotipo, si lo hay, subido al sitio | Su ruta `/files/...` abre en el navegador |
| La estructura de la institución en hojas de cálculo | Ver el paso 2 |

## 1. Escribir el perfil

El perfil es un YAML con cuatro bloques. Copiar el ejemplo comentado del producto,
`sgc/setup/perfil-institucion.ejemplo.yaml`, a **la capa de la institución** (nunca al
repositorio del producto) y rellenarlo:

| Bloque | Qué declara | Obligatorio |
|---|---|---|
| `institucion` | `nombre` (encabeza los documentos), `sistema` (cómo se llama el SGC), `logo`, `favicon`, `copyright` | `nombre` |
| `identidad_digital` | `issuer`, `client_id`, `client_secret_env`, `etiqueta`, `proveedor`, `rutas`, `habilitado` | no |
| `pais` | `marcos`: los marcos normativos a cargar | no |
| `estructura` | ruta a la carpeta de hojas o al `.xlsx` | no, pero sin ella la instancia queda bloqueada |

**El secreto del proveedor de identidad nunca va en el perfil**, que suele versionarse. El
perfil nombra una variable de entorno (`client_secret_env`) y el secreto se exporta en ella al
lanzar el comando. Si el perfil trae `client_secret`, el alta se niega.

Las rutas relativas del perfil parten de la carpeta del propio perfil.

## 2. Preparar la estructura

Cuatro hojas: `unidades`, `programas`, `programas-sede` y `periodos`, con las columnas que
describe [Instalación → Cargar la estructura](../instalacion/#cargar-la-estructura-de-la-institución).
Partir de las plantillas de ejemplo (`/assets/sgc/plantillas/estructura/` en el sitio). Tres
reglas que el alta comprueba y que conviene tener presentes al rellenarlas:

- El árbol de unidades tiene **una sola raíz**: la institución.
- Las referencias son **códigos** (`padre`, `sede`, `facultad`, `escuela`, `programa`).
- Tiene que haber un periodo `abierto`, con sus fechas.

## 3. Lanzar el alta

~~~bash
export SGC_SSO_CLIENT_SECRET='…'   # solo si el perfil declara identidad_digital
bench --site SITIO execute sgc.setup.alta_institucion.run --kwargs "{'perfil': '/ruta/perfil.yaml'}"
~~~

Qué hace, en orden:

1. **Valida el perfil entero**, incluida la estructura contra lo que ya hay en el sitio y la
   existencia de cada marco. Si algo falla, no escribe nada y lista todo lo que falta.
2. **Configuración del sitio**: escribe en `site_config.json` solo las claves que el perfil
   declara y que cambian.
3. **Arranque común**: los pasos del despliegue, que aplican la identidad, el inicio de sesión
   institucional y los marcos del perfil de país, además de permisos, flujos y avisos.
4. **Estructura**: importa las hojas, todo o nada.
5. **Verificación de instancia**: lo que falta para estar operable.

Lo que debe salir al final:

~~~text
[4/4] verificación de instancia
…
N hallazgo(s); 0 bloqueante(s).
Alta terminada: sin bloqueantes.
~~~

Y el `redirect_uri` exacto que hay que tener registrado en el proveedor de identidad sale en
la línea `SSO creado: …` del paso 3.

## 4. Si algo sale mal

| Mensaje | Qué pasó | Qué hacer |
|---|---|---|
| `Alta NO iniciada — perfil no válido` | El perfil o la estructura no pasan la validación. **No se ha escrito nada.** | Corregir cada línea de la lista y volver a lanzar |
| `Alta DETENIDA en <paso>` | Un paso falló. Lo anterior a ese paso quedó aplicado | Ver el Error Log del sitio (título `alta_institucion: fallo en …`), corregir y volver a lanzar |
| `Alta terminada, pero la instancia TIENE BLOQUEANTES` | El alta se hizo, y falta algo sin lo que no se puede trabajar | Cada bloqueante dice qué hacer |

**Volver a lanzar siempre es seguro.** El alta es idempotente: con el mismo perfil no escribe
ninguna clave, no duplica marcos ni unidades y no cambia lo que ya está bien. Lo que el perfil no
declara no se toca: quitar `identidad_digital` del perfil no apaga un inicio de sesión que ya
exista.

En los tres casos el comando termina con código de salida 1, y con 0 si todo fue bien: se
puede encadenar en un despliegue automatizado.

## 5. Después del alta

Lo que la verificación suele señalar todavía, y que el alta no hace a propósito:

- **Correo** (`correo-sin-cuenta-saliente`): crear la cuenta de correo saliente del sitio.
- **Tareas programadas** (`scheduler-parado`): en un sitio nuevo el scheduler nace apagado;
  `bench --site SITIO scheduler enable`.
- **Responsables de proceso** (`procesos-sin-responsable`): los asigna Calidad cuando cargue sus
  procesos.

La verificación se puede repetir cuando se quiera:

~~~bash
bench --site SITIO execute sgc.verificacion.run
~~~
