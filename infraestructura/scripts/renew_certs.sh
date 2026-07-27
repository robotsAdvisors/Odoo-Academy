#!/bin/bash
# =============================================================
# renew_certs.sh — Renovación automática de certificados Let's Encrypt
#
# Certbot renueva solo si faltan menos de 30 días para expirar.
# Let's Encrypt expira a los 90 días → renovación efectiva cada ~60 días.
# Ejecutarlo a diario es correcto: los días que no toca, no hace nada.
#
# Agregar al crontab del VPS (crontab -e):
#   0 3 * * * /ruta/absoluta/infraestructura/scripts/renew_certs.sh >> /var/log/certbot-renew.log 2>&1
# =============================================================

set -uo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*"; }

log "Iniciando renovación de certificados..."

# Cada renovación deja su marca en /var/www/certbot/.renewed para que
# sepamos si hay que recargar nginx o no.
"${COMPOSE[@]}" run --rm --entrypoint certbot certbot \
    renew \
    --webroot \
    --webroot-path=/var/www/certbot \
    --deploy-hook "touch /var/www/certbot/.renewed" \
    --quiet
RC=$?

# Nota: sin esta captura explícita, un 'if [ $? -eq 0 ]' colocado tras
# el comando siempre vería el código del último builtin, no el de certbot.
if [ "$RC" -ne 0 ]; then
    log "ERROR: certbot salió con código ${RC}. Revisa los logs."
    exit 1
fi

# ¿Renovó algo realmente?
if "${COMPOSE[@]}" run --rm --entrypoint sh certbot \
       -c 'test -f /var/www/certbot/.renewed && rm -f /var/www/certbot/.renewed'; then
    log "Certificados renovados. Recargando nginx..."
    # El servicio se llama 'nginx' en docker-compose.yml (no 'odoo_nginx')
    if "${COMPOSE[@]}" exec -T nginx nginx -s reload; then
        log "Renovación completada."
    else
        log "ERROR: no se pudo recargar nginx. Los certs nuevos no están activos."
        exit 1
    fi
else
    log "Nada que renovar (ningún certificado expira en menos de 30 días)."
fi
