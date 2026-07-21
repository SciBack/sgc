---
title: Roles y permisos
description: Guías independientes para probar los 14 roles efectivos del SGC.
sidebar:
  order: 1
---

El catálogo vigente contiene 13 roles propios de SGC y System Manager de Frappe. Los permisos efectivos resultan de tres capas: DocPerm, workflow y, cuando existen, User Permissions por ámbito. Un botón oculto no sustituye una comprobación de autorización en backend.

Para la regresión usa una cuenta separada por rol. No acumules roles en una sola cuenta porque produciría falsos positivos. Revisa cada guía y registra tanto acciones permitidas como denegadas.

:::note[Estados parciales]
Responsable de Sede y Lector Externo están marcados como parciales por comentarios y configuración del código; la guía no inventa capacidades que todavía no estén implementadas.
:::
