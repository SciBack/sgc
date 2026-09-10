"""F20 — Corrige la `categoria` de los Indicador que dicen ser de acreditación sin serlo.

El campo `categoria` de Indicador es **filtro estándar** en la lista, así que es lo
primero que alguien pulsa para ver «los indicadores de acreditación». Y estaba
mintiendo: en producción, los únicos cinco marcados como `Acreditacion` eran los
conteos operativos que publica MidPoint (`MP-DOCENTES`, `MP-ESTUDIANTES`,
`MP-RATIO-DOC-EST`…), que no tributan a ningún marco normativo — mientras que los
del modelo Coneau (`ID6`, `ID10`, `INST-ID11/12/13`) figuraban como `Proceso`.
Quien filtrara por `Acreditacion` obtenía cinco indicadores que no acreditan nada
y ni uno solo de los que sí.

**El criterio que se aplica aquí:** `categoria` describe la NATURALEZA del dato
(de proceso, de satisfacción, de gestión); la finalidad normativa la declara
`marco_normativo`, que es el campo fiable y el que usa `sgc.marcos`. Por tanto
nada es «de acreditación» por categoría: un indicador acredita porque su marco
acredita. Los que se declaran `Acreditacion` sin un marco de acreditación detrás
pasan a `Gestion`.

Por qué es un paso de despliegue y no un arreglo a mano: los `MP-*` no se crean
en este repo, los escribe un conector externo. Corregir la base una vez no impide
que el conector los vuelva a marcar mal. Esto se ejecuta en cada `migrate`, así
que recoloca lo que haya llegado torcido.

Deliberadamente NO se valida en `Indicador.validate`: reventar ahí rompería la
ingesta del productor externo, y un dato mal etiquetado no justifica perder la
medición. Se corrige después, no se bloquea antes.

Idempotente: en un sitio ya corregido no escribe nada.

Ejecutar:
    bench --site <site> execute sgc.setup.f20_categoria_indicador.run
"""
import frappe

from sgc import marcos

# Los conteos operativos sin marco normativo son indicadores de gestión.
CATEGORIA_DESTINO = "Gestion"


def run():
    sospechosos = frappe.get_all(
        "Indicador",
        filters={"categoria": "Acreditacion"},
        fields=["name", "marco_normativo"],
        limit_page_length=0,
    )

    cambios = []
    for ind in sospechosos:
        if marcos.es_de_acreditacion(ind.marco_normativo):
            continue  # dice acreditación y su marco lo respalda: se respeta
        frappe.db.set_value("Indicador", ind.name, "categoria", CATEGORIA_DESTINO, update_modified=False)
        cambios.append((ind.name, ind.marco_normativo or "sin marco"))

    frappe.db.commit()

    print(
        "F20 categoria indicador: %d con categoria=Acreditacion, %d recolocado(s) a %s"
        % (len(sospechosos), len(cambios), CATEGORIA_DESTINO)
    )
    for name, marco in cambios:
        print("   %-18s (%s) -> %s" % (name, marco, CATEGORIA_DESTINO))

    return {"revisados": len(sospechosos), "cambios": cambios}
