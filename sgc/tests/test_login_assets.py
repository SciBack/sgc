# Copyright (c) 2026, SciBack and Contributors
# See license.txt

"""Contrato estatico de la mejora progresiva del login."""

from pathlib import Path
from unittest import TestCase


class TestLoginAssets(TestCase):
	def test_javascript_conserva_el_login_nativo_y_sus_fallbacks(self):
		js = (
			Path(__file__).resolve().parents[1] / "public" / "js" / "sgc_web.js"
		).read_text(encoding="utf-8")

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
