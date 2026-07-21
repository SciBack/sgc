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
2. Autentícate con una cuenta de un solo rol. Resultado: carga la SPA y se obtiene la sesión.
3. Recorre los módulos visibles. Resultado: solo se muestran entradas compatibles con roles.
4. Abre manualmente una ruta no autorizada. Resultado: backend rechaza los datos aunque la URL exista.
5. Cierra sesión. Resultado: las rutas protegidas vuelven a pedir autenticación.

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

## Relación con otros módulos

Todos los módulos, router y store de sesión.

## Acciones operativas o configuración adicional

Keycloak/SSO requiere proveedor disponible; el login local debe conservarse.

## Fuente en código

frontend/src/router.js y frontend/src/stores/session.js. El comportamiento descrito debe revisarse de nuevo si estas fuentes cambian.

