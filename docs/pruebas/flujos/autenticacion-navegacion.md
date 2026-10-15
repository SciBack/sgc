---
title: Autenticación y navegación
description: Prueba funcional del proceso Autenticación y navegación.
---

## Quién puede ejecutarlo

Cualquier usuario habilitado; los menús dependen de sus roles.

## Precondiciones

Cuenta activa en Frappe/Keycloak.

## Pasos y resultados esperados

1. Abre una ruta protegida sin sesión. Resultado: el sistema redirige al login.
2. Autentícate con una cuenta de un solo rol. Resultado: carga el Desk de Frappe y se obtiene la sesión.
3. Recorre los Workspaces y módulos visibles. Resultado: solo se muestran entradas compatibles con roles. El **Inicio** muestra los accesos del día a día, el estado del sistema en cifras y una tarjeta por área. Su barra lateral lleva a las nueve áreas, en este orden: **Procesos, Documentos, Indicadores, Acreditación y licenciamiento, Mejora continua, Auditoría, Riesgos, Dirección y partes interesadas y Configuración**. Cada área tiene su portada, con sus cifras y gráficos, y su propia barra, que repite exactamente las pantallas de la portada. Una pantalla está en un solo menú, y la miga es siempre ⌂ / Área / Pantalla / Registro. Lo que el rol no puede abrir no aparece: la DPGC, por ejemplo, no ve la configuración de correo ni de soporte. Quien no ve la portada general entra directamente en la primera área que sí ve: un **Colaborador**, por ejemplo, aterriza en **Riesgos**, donde reporta los eventos de riesgo.
4. Abre una misma pantalla por tres caminos: desde el Inicio, desde otra pantalla y desde la portada de otra área. Resultado: la miga de pan es siempre **⌂ > Área > Pantalla** (y **> Registro** en un formulario), con nombres en español y el área enlazada a su portada. También en la vista árbol (Proceso, Unidad orgánica, Estándar o criterio) y en los informes.
5. Abre manualmente una ruta no autorizada. Resultado: backend rechaza los datos aunque la URL exista.
6. Cierra sesión. Resultado: las rutas protegidas vuelven a pedir autenticación.

## Estados por los que pasa

Sin sesión → autenticando → sesión activa → sesión cerrada. Este proceso no añade estados distintos a los que persisten sus DocTypes o sesión.

## Permisos

Verifica permisos de lectura/escritura sobre cada DocType y la autorización del método backend. La visibilidad de interfaz no reemplaza el control del servidor.

## Restricciones

No aceptar una cookie auxiliar como sesión; no considerar el menú como única barrera.

## Casos negativos

- Repetir el método para comprobar idempotencia o rechazo consistente.
- Ejecutar con rol o ámbito no autorizado.
- Omitir una precondición y conservar el mensaje exacto.
- Confirmar que el fallo no deja cambios parciales.

## Evidencia que debe capturarse

Estado o valores antes/después, identificador ficticio, rol, URL/método, respuesta y logs correlacionables sin cookies, tokens ni datos personales.

## Contraseña con elementos seguros

Además de la fuerza que mide Frappe (entropía, **Puntuación mínima de contraseña** en la configuración del sistema), una contraseña necesita **al menos 8 caracteres, una mayúscula, una minúscula y un número**. Se aplica al fijarla desde el formulario del usuario, al restablecerla o cambiarla desde **Actualizar contraseña**, y en el medidor de la pantalla, que avisa antes de enviar.

- Caso negativo: una contraseña sin mayúsculas, sin minúsculas, sin números o de menos de 8 caracteres se rechaza con el motivo.
- Quien entra por SSO no usa contraseña del SGC: la regla no le afecta.
- Se desactiva por sitio con `sgc_contrasena_clases: 0` en `site_config.json`, y también cuando la política de contraseñas de Frappe está apagada.

## Relación con otros módulos

Todos los módulos, Workspaces, DocTypes y sesión de Frappe.

## Acciones operativas o configuración adicional

El botón de inicio de sesión con la cuenta institucional aparece solo si el sitio declara su proveedor de identidad en `site_config.json` (claves `sgc_sso_*`); lo aplica cada `migrate`. Sin esa configuración se entra con usuario y contraseña, y la verificación de la instancia lo indica como `sso-no-configurado`. La cuenta se enlaza **por correo**: si el correo que entrega el proveedor no coincide con el del usuario en el SGC, el botón no deja entrar. El login local debe conservarse como red de seguridad mientras no se haya probado el SSO con cada persona.

## Fuente en código

La configuración de autenticación del site, los roles y permisos de Frappe. No hay una capa
propia de navegación ni un store de sesión adicional que mantener.
