"""Contrato del endpoint usado por el forward-auth del manual."""

import frappe
from frappe.tests import IntegrationTestCase

from sgc.manual_auth import LOGIN_LOCATION, authorize


class IntegrationTestManualAuth(IntegrationTestCase):
    def setUp(self):
        self.previous_user = frappe.session.user
        self.previous_form_dict = frappe.local.form_dict
        self.previous_response = frappe.local.response
        frappe.local.response = {}

    def tearDown(self):
        frappe.set_user(self.previous_user)
        frappe.local.form_dict = self.previous_form_dict
        frappe.local.response = self.previous_response

    def test_authenticated_session_returns_204_without_identity(self):
        frappe.set_user("Administrator")

        self.assertIsNone(authorize())

        self.assertEqual(frappe.local.response["http_status_code"], 204)
        self.assertNotIn("user", frappe.local.response)
        self.assertIn("no-store", frappe.local.response["headers"]["Cache-Control"])

    def test_guest_redirects_to_fixed_manual_login(self):
        frappe.set_user("Guest")

        self.assertIsNone(authorize())

        self.assertEqual(frappe.local.response["http_status_code"], 302)
        self.assertEqual(frappe.local.response["location"], LOGIN_LOCATION)
        self.assertEqual(frappe.local.response["type"], "redirect")

    def test_request_cannot_override_redirect_target(self):
        frappe.set_user("Guest")
        frappe.local.form_dict = frappe._dict({"redirect_to": "https://example.invalid"})

        authorize()

        self.assertEqual(frappe.local.response["location"], LOGIN_LOCATION)
