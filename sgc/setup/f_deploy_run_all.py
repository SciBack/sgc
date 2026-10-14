"""Orquestador de despliegue — lo único del SGC que depende de cada instancia.

Desde la 1.2.0 casi todo el SGC viene como documentos estándar de Frappe, que el propio
`migrate` sincroniza sin código del SGC (ver `sgc/estandar.py` y `sgc/escritorio.py`):
DocTypes con sus permisos, workflows con sus estados y acciones, roles y perfiles (fixtures),
avisos, formatos de impresión, portadas, menús, cifras y gráficos. Hasta la 1.1.0 lo creaban
29 pasos en cada `migrate`, y eso es lo que rompía al actualizar Frappe.

Aquí queda solo lo que cambia de una institución a otra, porque sale de su `site_config`:

  1. marcos_normativos  — los marcos que la instancia declara en `sgc_marcos` (#47)
  2. f17_alcance_marcos — clasifica esos marcos (licenciamiento / acreditación)
  3. f3b_branding       — identidad visual del Desk; neutra si no se declara
  4. f3b_sso            — inicio de sesión institucional (OIDC); sin `sgc_sso_issuer` no hace
                          nada y lo dice (#46)
  5. f20_categoria_indicador — recoloca los indicadores que un conector externo vuelve a marcar
                          como de acreditación sin serlo: es dato que llega torcido, no config

Ejecutar manualmente:
    bench --site <site> execute sgc.setup.f_deploy_run_all.run
Se ejecuta también solo, vía `after_migrate` (ver hooks.py).
"""
import os
import re
import time

import frappe

# Los locks de DOCUMENTO de Frappe se nombran con el hash del documento
# (frappe/utils/file_lock.py); los del framework tienen nombre legible
# (`bench_migrate`, `scheduler`…). Solo los primeros son seguros de borrar.
_ES_LOCK_DE_DOCUMENTO = re.compile(r"[0-9a-f]{16,}")

from sgc.setup import (
    f3b_branding,
    f3b_sso,
    f17_alcance_marcos,
    f20_categoria_indicador,
    marcos_normativos,
)

STEPS = [
    ("marcos_normativos", marcos_normativos),
    ("f17_alcance_marcos", f17_alcance_marcos),
    ("f3b_branding", f3b_branding),
    ("f3b_sso", f3b_sso),
    ("f20_categoria_indicador", f20_categoria_indicador),
]


def _correr_paso(name, mod, reintentos=2):
    """Ejecuta un paso, reintentando si el DocType quedó bloqueado por el propio migrate.

    Cuando un deploy cambia el .json de un DocType, `bench migrate` lo sincroniza y lo
    deja LOCKED/encolado. Como este orquestador corre en `after_migrate`, un paso que
    escriba sobre ese mismo DocType revienta con `DocumentLockedError` — y el RBAC se queda sin
    reaplicar en producción, en silencio salvo por el Error Log.

    El lock es transitorio: liberarlo y reintentar basta (verificado en el lab 2026-07-27,
    donde el paso suelto pasaba y dentro de migrate no). Se reintenta SOLO ante lock, no
    ante cualquier error: un fallo real debe seguir fallando.
    """
    for intento in range(reintentos + 1):
        try:
            mod.run()
            frappe.db.commit()
            return True
        except frappe.exceptions.DocumentLockedError:
            frappe.db.rollback()
            if intento == reintentos:
                raise
            # Los locks de documento de Frappe son ARCHIVOS en sites/<site>/locks/
            # (frappe/utils/file_lock.py), no entradas de caché. Los que deja el propio
            # migrate ya no tienen proceso detrás cuando llegamos a after_migrate, así
            # que se borran los caducados y se reintenta.
            # ⚠️ En ese MISMO directorio viven también los locks con nombre del
            # framework — sobre todo `bench_migrate.lock`, que crea
            # `frappe.utils.synchronization.filelock` y es lo que impide que dos
            # `bench migrate` corran a la vez. Borrarlo dejaría el sitio sin esa
            # protección justo durante un despliegue. Por eso NO se barre el
            # directorio: solo se borran los locks de DOCUMENTO, cuyo nombre es un
            # hash hexadecimal (`create_lock(name)` sobre el hash del doc), nunca
            # un lock con nombre legible como `bench_migrate` o `scheduler`.
            try:
                locks_dir = frappe.get_site_path("locks")
                if os.path.isdir(locks_dir):
                    for f in os.listdir(locks_dir):
                        if not f.endswith(".lock"):
                            continue
                        if not _ES_LOCK_DE_DOCUMENTO.fullmatch(f[: -len(".lock")]):
                            continue  # lock con nombre del framework: intocable
                        try:
                            os.remove(os.path.join(locks_dir, f))
                        except FileNotFoundError:
                            pass  # otro proceso lo liberó primero
            except Exception:
                pass
            time.sleep(2)
    return False


def run():
    ok, fallidos = [], []
    for name, mod in STEPS:
        try:
            _correr_paso(name, mod)
            ok.append(name)
        except Exception:
            frappe.db.rollback()
            fallidos.append(name)
            frappe.log_error(title=f"f_deploy_run_all: fallo en {name}")
            print(f"  [FALLO] {name} — ver Error Log")
    # Los pasos corren con `in_patch`, y con él Frappe construye el meta SIN los
    # Custom DocPerm (`frappe/model/meta.py:642`): cualquier meta que un paso haya
    # dejado en caché va sin la matriz RBAC. Se tira toda la caché al acabar para
    # que un `migrate` sin `clear-cache` no deje a los roles sin permisos.
    frappe.flags.in_patch = False
    frappe.clear_cache()
    print("=" * 60)
    print("F_DEPLOY_RUN_ALL — RESUMEN")
    print("=" * 60)
    print("OK:", ", ".join(ok) if ok else "(ninguno)")
    if fallidos:
        print("FALLIDOS:", ", ".join(fallidos), "— revisar Error Log antes de continuar")
    return {"ok": ok, "fallidos": fallidos}
