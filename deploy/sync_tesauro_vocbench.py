#!/usr/bin/env python3
"""Re-sincroniza el catálogo `Termino Tesauro` desde VocBench (Tesauro Institucional UPeU).

VocBench vive en la LAN interna de UPeU (192.168.15.231) y NO es alcanzable desde
el EC2 de producción. Por eso el catálogo NO se sincroniza en vivo: este script se
corre desde una máquina con la VPN corporativa, regenera el fixture versionado
`sgc/fixtures/termino_tesauro.json`, y el cambio llega a prod por el flujo normal
(commit → push → git pull → bench migrate, que reimporta el fixture).

Fuente de verdad: VocBench. Este fixture es una copia. Correr cuando el tesauro cambie.

Uso:
    source ~/.secrets/vocbench-upeu.env    # VOCBENCH_USER, VOCBENCH_PASS, VOCBENCH_PROJECT
    python3 deploy/sync_tesauro_vocbench.py

Requisitos: VPN corporativa activa (para alcanzar 192.168.15.231:1979).

Esquemas sincronizados (SKOS-XL): Temas, ISCED-F 2013, Líneas de Investigación.
El código de cada término = "{tipo}-{localname}" derivado de la URI SKOS (estable).
"""
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import defaultdict
from http.cookiejar import CookieJar

ST_HOST = os.environ.get("VOCBENCH_ST_HOST", "192.168.15.231")
ST_PORT = os.environ.get("VOCBENCH_ST_PORT", "1979")
ST = f"http://{ST_HOST}:{ST_PORT}/semanticturkey/it.uniroma2.art.semanticturkey/st-core-services"
PROJECT = os.environ.get("VOCBENCH_PROJECT", "Tesauro_Institucional_UPeU")
USER = os.environ.get("VOCBENCH_USER")
PASS = os.environ.get("VOCBENCH_PASS")

# esquema slug (segmento .../scheme/<slug>) -> etiqueta del Select en Frappe
ESQUEMAS = {
    "temas": "Temas",
    "isced-f-2013": "ISCED-F 2013",
    "lineas-de-investigacion": "Líneas de Investigación",
}

FIXTURE = os.path.join(os.path.dirname(__file__), "..", "sgc", "fixtures", "termino_tesauro.json")

_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(CookieJar()))


def _post(url, data):
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(url, data=body)
    with _opener.open(req, timeout=40) as r:
        return json.loads(r.read().decode())


def login():
    if not (USER and PASS):
        sys.exit("Faltan VOCBENCH_USER / VOCBENCH_PASS. Corre: source ~/.secrets/vocbench-upeu.env")
    _post(f"{ST}/Auth/login", {"email": USER, "password": PASS})


def sparql(query):
    d = _post(f"{ST}/SPARQL/evaluateQuery", {"query": query, "ctx_project": PROJECT})

    def find(o):
        if isinstance(o, dict):
            if "bindings" in o:
                return o["bindings"]
            for v in o.values():
                r = find(v)
                if r is not None:
                    return r
        return None

    return find(d) or []


def extract():
    q = """PREFIX skos: <http://www.w3.org/2004/02/skos/core#>
PREFIX skosxl: <http://www.w3.org/2008/05/skos-xl#>
SELECT ?c (STR(?scheme) AS ?s) (STR(?lab) AS ?label) WHERE {
  ?c a skos:Concept ; skos:inScheme ?scheme .
  { ?c skosxl:prefLabel/skosxl:literalForm ?lab } UNION { ?c skos:prefLabel ?lab }
}"""
    por = defaultdict(dict)  # scheme_uri -> {concept_uri: label}
    for x in sparql(q):
        s = (x.get("s") or {}).get("value", "")
        lab = (x.get("label") or {}).get("value")
        uri = (x.get("c") or {}).get("value")
        if lab and uri:
            por[s][uri] = lab
    return por


def build_rows(por):
    rows = []
    for scheme_uri, items in por.items():
        slug = scheme_uri.rstrip("/").split("/")[-1].split("#")[-1]
        if slug not in ESQUEMAS:
            continue
        esquema = ESQUEMAS[slug]
        for uri, label in items.items():
            parts = uri.rstrip("/").split("/")
            tipo, local = parts[-2], parts[-1]
            codigo = f"{tipo}-{local}"
            rows.append({
                "doctype": "Termino Tesauro",
                "name": codigo,
                "codigo": codigo,
                "esquema": esquema,
                "nombre": label,
                "uri": uri,
                "sincronizado_de": "VocBench — Tesauro_Institucional_UPeU",
            })
    rows.sort(key=lambda r: (r["esquema"], r["nombre"].lower()))
    names = [r["name"] for r in rows]
    dups = {n for n in names if names.count(n) > 1}
    if dups:
        sys.exit(f"Códigos duplicados (colisión de localname entre esquemas): {sorted(dups)}")
    return rows


def main():
    login()
    rows = build_rows(extract())
    if not rows:
        sys.exit("0 términos extraídos — revisa la VPN y el proyecto VocBench.")
    with open(FIXTURE, "w") as f:
        json.dump(rows, f, indent=1, ensure_ascii=True, sort_keys=True)
        f.write("\n")
    from collections import Counter
    c = Counter(r["esquema"] for r in rows)
    print(f"Fixture actualizado: {len(rows)} términos -> {os.path.relpath(FIXTURE)}")
    for k, v in sorted(c.items()):
        print(f"  {v:4d}  {k}")
    print("\nSiguiente: git add sgc/fixtures/termino_tesauro.json && commit && push && (en prod) git pull && bench migrate")


if __name__ == "__main__":
    main()
