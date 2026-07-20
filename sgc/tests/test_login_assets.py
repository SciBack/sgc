# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Contrato estatico de la mejora progresiva del login."""

import re
from pathlib import Path
from unittest import TestCase


class TestLoginAssets(TestCase):
	def setUp(self):
		public = Path(__file__).resolve().parents[1] / "public"
		self.css = (public / "css" / "sgc_web.css").read_text(encoding="utf-8")
		self.js = (public / "js" / "sgc_web.js").read_text(encoding="utf-8")

	def test_javascript_conserva_el_login_nativo_y_sus_fallbacks(self):
		js = self.js

		self.assertIn(
			'URLSearchParams(window.location.search).get("login_local") === "1"', js
		)
		self.assertIn("a.btn-keycloak", js)
		self.assertIn("sgc.login_portada.metricas_portada", js)
		self.assertIn("AbortSignal.timeout(4000)", js)
		self.assertNotIn("oauth2_logins", js)

		for texto in (
			"Dirección de Gestión de la Calidad",
			"Calidad que se demuestra.",
			"Acreditación, evidencias y mejora continua — conectadas, trazables y medibles.",
			"SGC",
			"Bienvenido al SGC",
			"Ingresar con mi cuenta UPeU",
			"© 2026 SGC UPeU · Universidad Peruana Unión · Dirección de Gestión de la Calidad",
		):
			self.assertIn(texto, js)

		for asset in (
			"/assets/sgc/media/login/oficinas-dti.mp4",
			"/assets/sgc/media/login/oficinas-dti-poster.jpg",
			"/assets/sgc/media/login/upeu-logo-2026-white.svg",
		):
			self.assertIn(asset, js)

	def test_css_declara_la_composicion_responsive_completa(self):
		for selector in (
			".sgc-login-cover",
			".sgc-login-video",
			".sgc-login-hero",
			".sgc-login-stats",
			".sgc-login-card-slot",
			".sgc-login-card",
			".sgc-login-cta",
		):
			self.assertIn(selector, self.css)

		self.assertIn("@media (min-width: 1024px)", self.css)
		self.assertIn("@media (prefers-reduced-motion: reduce)", self.css)
		self.assertIn(":focus-visible", self.css)
		self.assertRegex(self.css, r"min-height:\s*44px")
		self.assertRegex(
			self.css,
			re.compile(r"\.sgc-login-cover[^}]*box-sizing:\s*border-box", re.S),
		)
		self.assertIn("transform: scale(0.97)", self.css)
		self.assertRegex(
			self.css,
			re.compile(r"\.sgc-login-stat-bar-fill\s*\{[^}]*transform-origin:\s*left", re.S),
		)

	def test_css_carga_las_cuatro_fuentes_locales(self):
		fuentes = re.findall(r"@font-face\s*\{(.*?)\}", self.css, re.S)
		self.assertEqual(4, len(fuentes))
		for archivo in (
			"archivo-latin-700-normal.woff2",
			"public-sans-latin-400-normal.woff2",
			"public-sans-latin-600-normal.woff2",
			"public-sans-latin-700-normal.woff2",
		):
			self.assertIn(f"/assets/sgc/fonts/{archivo}", self.css)
		self.assertEqual(4, self.css.count("font-display: swap"))

	def test_css_evitar_patrones_de_movimiento_y_vidrio_no_aprobados(self):
		css_normalizado = re.sub(r"/\*.*?\*/", "", self.css, flags=re.S).lower()
		self.assertNotIn("transition: all", css_normalizado)
		self.assertNotIn("ease-in", css_normalizado)
		self.assertNotRegex(css_normalizado, r"scale\(0(?:\.0+)?\)")

		video = re.search(r"\.sgc-login-video\s*\{([^}]*)\}", css_normalizado, re.S)
		self.assertIsNotNone(video)
		self.assertNotIn("filter:", video.group(1))

		for regla in re.finditer(r"([^{}]+)\{([^{}]*backdrop-filter\s*:.*?)\}", css_normalizado, re.S):
			self.assertIn("sgc-login-stat", regla.group(1))

	def test_css_conserva_controles_reales_y_alertas_accesibles(self):
		self.assertIn('card.querySelector("a.btn-keycloak")', self.js)
		self.assertIn('guide.href = "https://', self.js)
		self.assertNotRegex(self.css, r"\[role\s*=\s*[\"']?alert[^}]*display:\s*none")
		self.assertRegex(
			self.css,
			re.compile(
				r"\.sgc-login-card[^}]*border:[^;]*var\(--color-marca-primaria-400\)",
				re.S,
			),
		)
