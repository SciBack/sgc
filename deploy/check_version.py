"""Coherencia de la versión publicada (#52). Sin Frappe: corre antes de construir nada.

Tres cosas tienen que decir lo mismo, y si no lo dicen la publicación es un fallo, no un detalle:

1. `sgc/__init__.py` (`__version__`), que es lo que Frappe registra en cada migrate y lo que
   devuelve el endpoint de estado (#53).
2. El tag de git que dispara la publicación (`v1.2.3`).
3. Una entrada fechada en `CHANGELOG.md` para esa versión.

Uso:

    python deploy/check_version.py               # versión válida y con entrada en el CHANGELOG
    python deploy/check_version.py --tag v1.2.3  # además, el tag coincide (lo usa release.yml)

Sale con 0 si todo cuadra y con 1 explicando qué no cuadra.
"""

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]

SEMVER = re.compile(r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$")
VERSION_APP = re.compile(r'^__version__\s*=\s*["\']([^"\']+)["\']', re.MULTILINE)
# «## [1.2.3] - 2026-10-13»: la fecha es obligatoria; una entrada sin fecha no está publicada.
ENTRADA = re.compile(r"^## \[(?P<version>[^\]]+)\] - (?P<fecha>\d{4}-\d{2}-\d{2})\s*$", re.MULTILINE)


class Incoherencia(Exception):
	pass


def version_app(raiz=RAIZ):
	texto = (raiz / "sgc" / "__init__.py").read_text(encoding="utf-8")
	m = VERSION_APP.search(texto)
	if not m:
		raise Incoherencia("sgc/__init__.py no declara __version__.")
	return m.group(1)


def version_de_tag(tag):
	"""«v1.2.3» → «1.2.3». Un tag que no sea vX.Y.Z no es una publicación."""
	if not tag.startswith("v") or not SEMVER.match(tag[1:]):
		raise Incoherencia(f"El tag «{tag}» no tiene la forma vX.Y.Z.")
	return tag[1:]


def entradas_changelog(raiz=RAIZ):
	ruta = raiz / "CHANGELOG.md"
	if not ruta.exists():
		raise Incoherencia("No existe CHANGELOG.md.")
	return {m.group("version"): m.group("fecha") for m in ENTRADA.finditer(ruta.read_text(encoding="utf-8"))}


def comprobar(raiz=RAIZ, tag=None):
	"""Devuelve la versión si todo cuadra; si no, lanza Incoherencia con el motivo."""
	version = version_app(raiz)
	if not SEMVER.match(version):
		raise Incoherencia(f"__version__ = «{version}» no es una versión semántica X.Y.Z.")
	if tag is not None and version_de_tag(tag) != version:
		raise Incoherencia(
			f"El tag «{tag}» no coincide con sgc/__init__.py («{version}»): "
			"se publicaría una imagen que dice ser otra versión."
		)
	if version not in entradas_changelog(raiz):
		raise Incoherencia(
			f"CHANGELOG.md no tiene una entrada «## [{version}] - AAAA-MM-DD» para la versión {version}."
		)
	return version


def main(argv=None):
	parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
	parser.add_argument("--tag", help="tag de git que se va a publicar (vX.Y.Z)")
	args = parser.parse_args(argv)
	try:
		version = comprobar(tag=args.tag)
	except Incoherencia as e:
		print(f"Versión incoherente: {e}", file=sys.stderr)
		return 1
	print(f"Versión coherente: {version}" + (f" (tag {args.tag})" if args.tag else ""))
	return 0


if __name__ == "__main__":
	sys.exit(main())
