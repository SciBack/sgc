// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';
import { readFileSync } from 'node:fs';

const site = process.env.DOCS_SITE;
if (!site) throw new Error('DOCS_SITE es obligatorio (ej. https://calidad.upeu.edu.pe)');
const siteUrl = new URL(site);
if (siteUrl.protocol !== 'https:') throw new Error('DOCS_SITE debe usar HTTPS');

const rawBase = process.env.DOCS_BASE || '/manual';
const base = `/${rawBase.replace(/^\/+|\/+$/g, '')}`;

// El manual describe UNA versión del SGC: la del código con el que se construye. Se lee de la
// única fuente (`sgc/__init__.py`), que viaja junto a `docs-site/` en el repo y en la imagen.
const versionFile = new URL('../sgc/__init__.py', import.meta.url);
const sgcVersion = readFileSync(versionFile, 'utf8').match(/__version__\s*=\s*"([^"]+)"/)?.[1];
if (!sgcVersion) throw new Error('No se encontró __version__ en sgc/__init__.py');

export default defineConfig({
  site: siteUrl.origin,
  base,
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    starlight({
      title: `Manual del SGC ${sgcVersion}`,
      description: 'Manual de usuario del Sistema de Gestión de la Calidad.',
      pagefind: true,
      tableOfContents: false,
      lastUpdated: true,
      customCss: ['./src/styles/sciback.css'],
      components: { Head: './src/components/Head.astro' },
      sidebar: [
        { label: 'Inicio', link: '/' },
        { label: 'Primeros pasos', link: '/primeros-pasos/' },
        { label: 'Qué hace cada perfil', link: '/perfiles/' },
        { label: 'Manual por área', items: [
          { label: 'Procesos', items: [{ autogenerate: { directory: 'procesos' } }] },
          { label: 'Documentos', items: [{ autogenerate: { directory: 'documentos' } }] },
          { label: 'Acreditación y licenciamiento', items: [{ autogenerate: { directory: 'acreditacion' } }] },
          { label: 'Mejora continua', items: [{ autogenerate: { directory: 'mejora-continua' } }] },
          { label: 'Configuración', items: [{ autogenerate: { directory: 'configuracion' } }] },
        ] },
      ],
    }),
  ],
});
