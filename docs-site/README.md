# Manual de usuario del SGC

Sitio Astro + Starlight con el **manual de usuario**: lo que necesita quien usa el SGC para
trabajar por su cuenta. Nada más. Las guías de prueba viven en [`docs/pruebas/`](../docs/pruebas/)
y la documentación técnica en [`docs/`](../docs/); no se publican aquí.

## Estructura

El menú sigue las áreas del menú del SGC, con los mismos nombres:

```
src/content/docs/
├── index.mdx            Inicio
├── primeros-pasos.md    Por dónde empezar, según el rol
├── perfiles.md          Qué hace cada perfil en cada flujo
├── procesos/            Un directorio por área del SGC.
├── documentos/          index.md es la página principal del área (sidebar.order: 1);
├── acreditacion/        el resto aparece solo en el menú, en orden alfabético
├── mejora-continua/     o según su sidebar.order.
└── configuracion/
```

Un área nueva se registra una vez en el `sidebar` de `astro.config.mjs`. Una página nueva dentro de
un área existente no necesita tocar la configuración.

## Versión

El manual describe **una** versión del SGC: la del código con el que se construye. El título del
sitio la lee de `sgc/__init__.py` («Manual del SGC 1.7.2»). Por eso, cuando un cambio altera lo
que ve el usuario, su página del manual se corrige **en la misma PR**. Detalle en
[`docs/desarrollo/versionado.md`](../docs/desarrollo/versionado.md).

## Reglas al escribir

- El repo es público: nada de una institución concreta (dominios, nombres, sedes). Lo propio de
  una institución va en su overlay.
- Enlaces entre páginas, relativos (`../acreditacion/`): el sitio se publica en dos bases.
- Frontmatter con `title` y `description`.

## Comandos

Las dos variables son obligatorias; cambian solo la marca y la base del sitio.

```bash
npm ci
export DOCS_SITE=https://calidad.example.edu DOCS_BASE=/manual
npm run dev        # http://localhost:4321/manual/
npm run verify     # config, cobertura, check, build, enlaces, privacidad, contraste, visual
```
