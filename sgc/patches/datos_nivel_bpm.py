"""`nivel_bpm` de los Proceso existentes, que hasta la 1.1.0 se recalculaba en cada `migrate`.

Lo nuevo ya lo deriva `Proceso.validate`; esto deja bien lo anterior, una sola vez (1.2.0).
"""

from sgc.setup import f19_nivel_bpm


def execute():
	f19_nivel_bpm.run()
