# Copyright (c) 2026, SciBack and contributors
# For license information, please see license.txt
"""Infraestructura de tests reutilizable del SGC.

Este paquete contiene *factories* idempotentes para construir el dato base que
casi todos los tests de negocio necesitan: el árbol Marco Normativo + Elemento
Marco (Estandar/Criterio), Autoevaluacion, Valoracion Criterio/Estandar, y los
objetos de M03 (Documento Controlado) y M09 (Evidencia/Trazabilidad).

Convención: TODO lo que crean estas factories usa el prefijo "TEST" en sus
códigos para no colisionar con datos reales (CONEAU-*, etc.). Los tests heredan
de `frappe.tests.IntegrationTestCase`, así que cada test corre en su propia
transacción con rollback automático; las factories no necesitan limpiar.
"""
