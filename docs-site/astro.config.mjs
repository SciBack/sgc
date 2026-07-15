// @ts-check
import { defineConfig } from 'astro/config';
import starlight from '@astrojs/starlight';

// https://astro.build/config
export default defineConfig({
	site: 'https://sciback.github.io',
	base: '/sgc',
	integrations: [
		starlight({
			title: 'SGC',
			description:
				'Documentación del producto canónico SciBack — eQMS para acreditación universitaria (CONEAU/SINEACE, CBC, ISO 21001).',
			social: [{ icon: 'github', label: 'GitHub', href: 'https://github.com/SciBack/sgc' }],
			tableOfContents: false,
			editLink: {
				baseUrl: 'https://github.com/SciBack/sgc/edit/main/docs-site/',
			},
			sidebar: [
				{ label: 'Arquitectura', link: '/arquitectura/' },
				{ label: 'Instalación', link: '/instalacion/' },
				{
					label: 'Módulos',
					items: [{ autogenerate: { directory: 'modulos' } }],
				},
				{
					label: 'Manual de uso',
					items: [{ autogenerate: { directory: 'manual-uso' } }],
				},
				{
					label: 'Desarrollo',
					items: [{ autogenerate: { directory: 'desarrollo' } }],
				},
			],
		}),
	],
});
