# Tests

Suite de integración Frappe (`bench run-tests`), con factories reutilizables y
cobertura enfocada en la lógica de negocio real (no en DocTypes triviales).

## Ejecutar la suite

Sobre cualquier bench Frappe con la app instalada y un site de desarrollo:

```bash
bench --site <tu-site> set-config allow_tests true
bench --site <tu-site> run-tests --app sgc
```

Un módulo específico:

```bash
bench --site <tu-site> run-tests --app sgc --module sgc.tests.test_scoring
```

## Factories

`sgc/tests/factories.py` centraliza la creación de datos de prueba (Autoevaluacion,
Proceso, Evidencia, etc.), idempotentes. Dos detalles importantes al escribir un test
nuevo:

- **`desactivar_workflow()`**: `Autoevaluacion` y `No Conformidad` tienen un Workflow
  nativo activo — asignar directamente un `estado` distinto al inicial dispara
  `WorkflowPermissionError` si el workflow sigue activo. Los tests que necesitan
  manipular el estado libremente deben desactivarlo primero.
- **`crear_evidencia`** usa por defecto `tipo="Enlace"` (evita depender de subir un
  archivo real en el entorno de test).
- Los códigos generados por las factories (p. ej. `crear_proceso`) se mantienen
  ≤12 caracteres de prefijo — ver el gotcha de correlativos abajo.

## Dónde está el valor real de la cobertura

De los DocTypes del sistema, la mayoría de "sin test" son **child tables con
controlador vacío** (sin lógica propia) — cubrirlos es cobertura de vanidad. El valor
real está en los módulos con lógica whitelisted:

- `scoring.py` (motor NL/L/LP)
- `confirmacion.py` (confirmación humana + vigencia)
- `capa.py` (cadena CAPA)
- `informe.py` (consolidación + PDF)
- `lista_maestra.py` (export)
- `www/*.py` (`get_context` de las páginas server-rendered)
- Los controladores con validación real (`documento_controlado.py`,
  `no_conformidad.py`, `evidencia.py`, `trazabilidad.py`)

## Gotcha: transacciones envenenadas en Postgres

Un test que dispara un error SQL sin rollback **envenena la transacción** — todos los
tests siguientes en la misma conexión fallan en cascada con
`current transaction is aborted`. Cuando veas una racha larga de fallos, **el primer
✖ es la causa real**; el resto son víctimas. No investigues el segundo fallo antes de
resolver el primero.

## Gotcha: correlativos de código por count()/len()

Los códigos autogenerados (`Documento Controlado`, `Evidencia`, entidades CAPA) deben
calcular su correlativo con `max(sufijo existente) + 1`, **nunca** con
`count()`/`len()` de los registros existentes — si se borra un registro intermedio,
`count()` reutiliza un número ya usado y choca con la restricción `unique` del código.
Ver `capa._next_codigo` y el helper equivalente en `documento_controlado.py` /
`evidencia.py` como referencia del patrón correcto.

## CI

El repo corre la suite en GitHub Actions (`.github/workflows/tests.yml`) sobre
PostgreSQL 16 + Frappe `version-16` en cada push/PR a `main`.
