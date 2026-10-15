---
title: Configuración (sgc_estructura)
description: Estructura institucional, datos e integraciones, y configuración del sistema.
sidebar:
  order: 9
---

Lo que el sistema necesita para funcionar en una institución concreta: su estructura organizacional,
las fuentes y reglas de los datos que recibe, y la configuración del correo y del soporte.

## Estructura organizacional

| DocType | Rol |
|---|---|
| **Unidad Organica** | Nodo de la estructura organizacional de la institución. |
| **Programa** | Un programa académico. |
| **Programa Sede** | La instancia de un Programa en una sede específica — es la unidad real sobre la que corre una Autoevaluación. |
| **Periodo Academico** | Periodo/ciclo académico usado para acotar mediciones y autoevaluaciones. |

## Datos, integraciones y sistema

| DocType | Rol |
|---|---|
| **Termino Tesauro** | Catálogo de lenguaje controlado sincronizado desde el tesauro institucional (VocBench/SKOS). No se edita a mano. |
| **Lote Ingesta** | Un lote recibido por la API de ingesta de indicadores (ver `docs/desarrollo/ingesta.md`). |
| **Configuracion Correo** | Cómo sale el correo de las reglas de notificación: en ensayo (no sale nada) o de verdad, y a quién. |
| **Registro Correo** | Correos que el sistema habría enviado y no envió, por estar en ensayo o fuera de la lista blanca. |
| **Configuracion Soporte** | Canal de soporte: a qué helpdesk llegan los problemas que se reportan desde el sistema. |
