"""Las fichas existentes recogen lo que el sistema ya sabe de su proceso (1.4.0).

Desde la 1.4.0 la ficha añade sola, al guardarse, los procedimientos, documentos, riesgos y
subprocesos de su proceso. Las ya creadas no se vuelven a guardar solas: esto lo hace una vez.

Además concilia los indicadores cargados fuera de la ficha (`Indicador.proceso` escrito por un
script sin la fila que lo declara): se declaran en su ficha, salvo los de acreditación o los
que ya declara otra. Sin pasar por `save`, para no regenerar PDFs ni mover estados aquí.
"""

import frappe


def execute():
	declarados = set(frappe.get_all("Indicador Proceso Link", filters={"parenttype": "Ficha Caracterizacion Proceso"},
									pluck="indicador"))
	for nombre in frappe.get_all("Ficha Caracterizacion Proceso", pluck="name"):
		ficha = frappe.get_doc("Ficha Caracterizacion Proceso", nombre)
		nuevas = ficha.completar_desde_el_sistema()
		if ficha.proceso:
			for ind in frappe.get_all("Indicador", filters={"proceso": ficha.proceso, "marco_normativo": ["is", "not set"]},
									  pluck="name", order_by="name asc"):
				if ind not in declarados:
					declarados.add(ind)
					nuevas.append(ficha.append("indicadores", {"indicador": ind}))
		for fila in nuevas:
			fila.db_insert()
		if nuevas:
			print(f"{nombre}: {len(nuevas)} fila(s) desde el sistema")
