#!/usr/bin/env bash
# Wrapper de cron para sincronizar el tesauro desde VocBench y publicarlo al repo.
#
# Corre en un host que ALCANCE VocBench (LAN 192.168.15.231): un host interno del
# segmento 192.168.15.x, o una máquina con la VPN corporativa. NO corre en el EC2
# de prod (no ve la LAN). El SGC en AWS recibe el cambio por su flujo normal
# (git pull + bench migrate reimporta el fixture). Ver README-tesauro-cron.md.
#
# Comportamiento: regenera el fixture; si NO cambió, no hace commit (idempotente).
# Si cambió, commit + push. Loguea con retención y avisa por Telegram ante fallo.
#
# Config por variables de entorno (todas con default):
#   SGC_REPO_DIR        raíz del repo canónico (con .git)   [default: ~/sgc]
#   SGC_TESAURO_BRANCH  rama a la que commitear              [default: main]
#   SGC_TESAURO_LOGDIR  carpeta de logs                      [default: ~/sgc-tesauro/logs]
# Secretos (source antes de correr, o el cron los exporta):
#   ~/.secrets/vocbench-upeu.env   VOCBENCH_USER / VOCBENCH_PASS / VOCBENCH_PROJECT
#   ~/.secrets/telegram.env        TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID  (opcional)
set -euo pipefail

REPO_DIR="${SGC_REPO_DIR:-$HOME/sgc}"
BRANCH="${SGC_TESAURO_BRANCH:-main}"
LOGDIR="${SGC_TESAURO_LOGDIR:-$HOME/sgc-tesauro/logs}"
FIXTURE="sgc/fixtures/termino_tesauro.json"

mkdir -p "$LOGDIR"
STAMP="$(date +%F_%H%M%S)"
LOG="$LOGDIR/sync_${STAMP}.log"

log() { echo "[$(date +%FT%T)] $*" | tee -a "$LOG"; }

alerta() {
	# Avisa por Telegram si hay credenciales; si no, solo queda en el log.
	local msg="$1"
	if [ -f "$HOME/.secrets/telegram.env" ]; then
		# shellcheck disable=SC1091
		source "$HOME/.secrets/telegram.env"
		if [ -n "${TELEGRAM_BOT_TOKEN:-}" ] && [ -n "${TELEGRAM_CHAT_ID:-}" ]; then
			curl -s --max-time 15 \
				"https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/sendMessage" \
				-d chat_id="${TELEGRAM_CHAT_ID}" \
				-d text="[SGC tesauro] ${msg}" >/dev/null || true
		fi
	fi
}

fallo() {
	log "ERROR: $1"
	alerta "FALLO $STAMP: $1 — ver $LOG"
	# retención: conservar los últimos 30 logs
	ls -1t "$LOGDIR"/sync_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f
	exit 1
}

# 1) secretos de VocBench
[ -f "$HOME/.secrets/vocbench-upeu.env" ] || fallo "falta ~/.secrets/vocbench-upeu.env"
# shellcheck disable=SC1091
source "$HOME/.secrets/vocbench-upeu.env"

# 2) repo en la rama correcta y al día
cd "$REPO_DIR" || fallo "no existe SGC_REPO_DIR=$REPO_DIR"
git rev-parse --is-inside-work-tree >/dev/null 2>&1 || fallo "$REPO_DIR no es un repo git"
git checkout "$BRANCH" >>"$LOG" 2>&1 || fallo "no pude cambiar a la rama $BRANCH"
git pull --quiet --ff-only >>"$LOG" 2>&1 || fallo "git pull falló (revisa conflictos)"

# 3) regenerar el fixture desde VocBench (requiere ver 192.168.15.231)
log "Consultando VocBench..."
python3 deploy/sync_tesauro_vocbench.py >>"$LOG" 2>&1 || fallo "el sync con VocBench falló (¿VPN/host?)"

# 4) ¿cambió el fixture?
if git diff --quiet -- "$FIXTURE"; then
	log "Sin cambios en el tesauro; no hay nada que commitear."
else
	N="$(git diff --numstat -- "$FIXTURE" | awk '{print $1"+/"$2"-"}')"
	log "El tesauro cambió ($N). Commiteando y publicando..."
	git add "$FIXTURE"
	git commit -q -m "chore(tesauro): sync automático desde VocBench ($STAMP)" >>"$LOG" 2>&1 || fallo "git commit falló"
	git push -q origin "$BRANCH" >>"$LOG" 2>&1 || fallo "git push falló (¿credenciales del host?)"
	log "Publicado. Prod aplicará en el próximo git pull + bench migrate."
	alerta "OK $STAMP: tesauro actualizado ($N) y publicado a $BRANCH."
fi

# 5) retención de logs
ls -1t "$LOGDIR"/sync_*.log 2>/dev/null | tail -n +31 | xargs -r rm -f
log "Fin."
