"""F3b branding — logo/favicon/nombre UPeU en el desk Frappe.
Ejecutar: bench --site sgc.localhost execute sgc.setup.f3b_branding.run
"""
import frappe

LOGO = "/files/membrete-upeu.png"
FAV = "/files/upeu-favicon.ico"


def _set(doc, **kw):
    for k, v in kw.items():
        if doc.meta.has_field(k):
            doc.set(k, v)


def run():
    frappe.flags.in_patch = True
    ws = frappe.get_doc("Website Settings")
    _set(ws,
         app_name="SGC UPeU",
         app_logo=LOGO,
         banner_image=LOGO,
         favicon=FAV,
         brand_html='<img src="{0}" style="height:24px;margin-right:6px"> SGC UPeU'.format(LOGO),
         copyright="Universidad Peruana Unión — Dirección de Gestión de la Calidad",
         disable_signup=1)
    ws.flags.ignore_permissions = True
    ws.save()
    try:
        ns = frappe.get_doc("Navbar Settings")
        _set(ns, app_logo=LOGO, logo_width=120)
        ns.flags.ignore_permissions = True
        ns.save()
    except Exception as e:
        print("navbar skip:", str(e)[:80])
    frappe.db.commit()
    print("branding OK — app_name=SGC UPeU, logo/favicon UPeU")
