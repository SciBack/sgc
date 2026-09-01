# Sincronización del tesauro (VocBench → SGC) como cron

El catálogo `Termino Tesauro` del SGC es una **copia versionada** del Tesauro
Institucional UPeU que vive en VocBench (`192.168.15.231`, LAN interna). El SGC en
AWS **nunca** llama a VocBench: solo lee el fixture `sgc/fixtures/termino_tesauro.json`
que viaja en el repo. Este cron mantiene ese fixture al día.

## Flujo

```
Host que ve VocBench (LAN/VPN)                         AWS / prod
  run_sync_tesauro.sh                                    git pull
    └─ sync_tesauro_vocbench.py → regenera el fixture      └─ bench migrate
    └─ si cambió: git commit + push  ───────────────────────► reimporta el fixture
```

Nada entrante hacia la LAN, nada saliente desde AWS. Mismo patrón que el conector de
indicadores de MidPoint (corre donde alcanza la fuente, empuja hacia afuera).

## Dónde instalarlo

Un host que **alcance `192.168.15.231`**, esté encendido y tenga salida a `github.com`:

- **Recomendado:** un host dentro del segmento `192.168.15.x` (p. ej. el propio server
  de VocBench `.231` o el lab `.150`). Ahí VocBench es local, no hace falta VPN.
- Alternativa: cualquier host con la VPN corporativa permanente.
- **No** el EC2 de prod: no ve la LAN.

## Requisitos en el host

1. Clonar el repo canónico y dejar credenciales de push (deploy key o token en el
   git credential helper — el script NO lleva secretos de git).
2. Copiar los secretos de VocBench:
   ```bash
   mkdir -p ~/.secrets && chmod 700 ~/.secrets
   # subir vocbench-upeu.env (VOCBENCH_USER, VOCBENCH_PASS, VOCBENCH_PROJECT), chmod 600
   ```
3. Opcional, para alertas: `~/.secrets/telegram.env` (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`).
4. `python3` disponible (usa solo stdlib, sin dependencias).

## Prueba manual antes del cron

```bash
SGC_REPO_DIR=~/sgc SGC_TESAURO_BRANCH=main bash deploy/run_sync_tesauro.sh
```

Revisa `~/sgc-tesauro/logs/sync_*.log`. Si el tesauro no cambió, no commitea (idempotente).

## Entrada de crontab (semanal, lunes 06:00)

El tesauro cambia poco; semanal es de sobra. Ajusta `SGC_TESAURO_BRANCH` a `main`
una vez que la rama `limpieza-frappe-nativo` esté mergeada.

```cron
0 6 * * 1 SGC_REPO_DIR=/home/USUARIO/sgc SGC_TESAURO_BRANCH=main /home/USUARIO/sgc/deploy/run_sync_tesauro.sh
```

## Qué hace ante cada situación

| Situación | Resultado |
|---|---|
| VocBench inalcanzable (sin VPN/host) | falla, alerta Telegram, **no** toca el repo |
| Tesauro sin cambios | log "sin cambios", **no** commitea |
| Tesauro cambió | commit + push a la rama, alerta OK |
| `git push` sin credenciales | falla con mensaje claro, alerta |

Logs con retención de los últimos 30 en `~/sgc-tesauro/logs/`.
