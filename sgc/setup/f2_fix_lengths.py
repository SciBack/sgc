"""F2 fixes de esquema previos al loader:
1. Deduplicar fieldnames en DocTypes árbol (is_group 2x: explícito + auto de is_tree).
2. Nombres/descr. largos CONEAU no caben en Data(140):
   - Indicador.nombre, Elemento Marco.denominacion -> Small Text
   - Ficha Indicador: TODOS los Data descriptivos -> Small Text (salvo codigo/unique)
"""
import frappe

SMALLTEXT_FIELDS = [("Indicador", "nombre"), ("Elemento Marco", "denominacion")]
SMALLTEXT_ALL = ["Ficha Indicador"]           # convertir todo Data descriptivo
TREES = ["Elemento Marco", "Unidad Organica", "Proceso"]
KEEP_DATA = {"codigo", "name", "sigla"}       # no convertir claves/naming


def run():
    frappe.flags.in_patch = True
    frappe.flags.in_fixtures = True
    dts = set(TREES) | set(SMALLTEXT_ALL) | {t[0] for t in SMALLTEXT_FIELDS}
    for dt in dts:
        d = frappe.get_doc("DocType", dt)
        seen, newf, removed, widened = set(), [], 0, 0
        for f in d.fields:
            if f.fieldname in seen:
                removed += 1
                continue
            seen.add(f.fieldname)
            # specific field widen
            if (dt, f.fieldname) in SMALLTEXT_FIELDS and f.fieldtype == "Data":
                f.fieldtype = "Small Text"; widened += 1
            # widen all descriptive Data in SMALLTEXT_ALL doctypes
            if dt in SMALLTEXT_ALL and f.fieldtype == "Data" \
               and f.fieldname not in KEEP_DATA and not f.get("unique"):
                f.fieldtype = "Small Text"; widened += 1
            newf.append(f)
        d.set("fields", newf)
        for i, f in enumerate(d.fields, 1):
            f.idx = i
        d.save()
        print(f"  {dt}: -{removed} dup, {widened} -> Small Text")
    frappe.db.commit()
    print("fix_lengths OK")
