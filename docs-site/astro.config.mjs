// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

const site = process.env.DOCS_SITE;
if (!site) throw new Error('DOCS_SITE es obligatorio (ej. https://calidad.upeu.edu.pe)');
const siteUrl = new URL(site);
if (siteUrl.protocol !== 'https:') throw new Error('DOCS_SITE debe usar HTTPS');

const rawBase = process.env.DOCS_BASE || '/manual';
const base = `/${rawBase.replace(/^\/+|\/+$/g, '')}`;

export default defineConfig({
  site: siteUrl.origin,
  base,
  output: 'static',
  trailingSlash: 'always',
  integrations: [
    starlight({
      title: 'Manual funcional SGC',
      description: 'Guía funcional verificable del Sistema de Gestión de la Calidad.',
      pagefind: true,
      tableOfContents: { minHeadingLevel: 2, maxHeadingLevel: 3 },
      lastUpdated: true,
      customCss: ['./src/styles/sciback.css'],
      components: { Head: './src/components/Head.astro' },
      sidebar: [
        { label: 'Inicio', link: '/' },
        { label: 'Propósito y mapa', link: '/proposito/' },
        { label: 'Roles y permisos', items: [{ autogenerate: { directory: 'roles' } }] },
        { label: 'Conceptos y reglas', link: '/conceptos/' },
        { label: 'Preparar pruebas', link: '/preparacion-pruebas/' },
        { label: 'Recorrido E2E', link: '/recorrido-e2e/' },
        { label: 'Flujos funcionales', items: [{ autogenerate: { directory: 'flujos' } }] },
        { label: 'Regresión', link: '/checklist-regresion/' },
        { label: 'Reportar hallazgos', link: '/reportar-hallazgo/' },
        { label: 'Administración', link: '/administracion/' },
        { label: 'Reportes y auditoría', link: '/reportes-auditoria/' },
        { label: 'Referencia técnica existente', collapsed: true, items: [
          { label: 'Arquitectura', link: '/arquitectura/' },
          { label: 'Instalación', link: '/instalacion/' },
          { label: 'Estado del producto', link: '/roadmap/' },
          { label: 'Módulos', items: [{ autogenerate: { directory: 'modulos' } }] },
          { label: 'Desarrollo', items: [{ autogenerate: { directory: 'desarrollo' } }] },
        ] },
      ],
    }),
  ],
});
