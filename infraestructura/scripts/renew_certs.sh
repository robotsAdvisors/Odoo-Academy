#!/bin/bash
# =============================================================
# renew_certs.sh — Renovación automática de certificados Let's Encrypt
#
# Certbot renueva solo si faltan menos de 30 días para expirar.
# Let's Encrypt expira a los 90 días → renovación cada ~60 días.
#
# Agregar al crontab del VPS (crontab -e):
#   0 3 * * * /ruta/absoluta/infraestructura/scripts/renew_certs.sh >> /var/log/certbot-renew.log 2>&1
# =============================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.yml"

echo "[$(date '+%Y-%m-%d %H:%M:%S')] Iniciando renovación de certificados..."

# Renovar — certbot solo actúa si el cert expira en < 30 días
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "" certbot \
  certbot renew --webroot --webroot-path=/var/www/certbot --quiet

# Recargar nginx solo si certbot renovó algo (exit 0 = renovó o no necesitaba)
if [ $? -eq 0 ]; then
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Recargando nginx..."
    docker compose -f "$COMPOSE_FILE" exec odoo_nginx nginx -s reload
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] Renovación completada."
else
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ERROR en la renovación. Revisa los logs de certbot."
    exit 1
fi
