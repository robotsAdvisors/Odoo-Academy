#!/bin/bash
# =============================================================
# init_certs.sh — Obtención inicial de certificados Let's Encrypt
# Ejecutar UNA SOLA VEZ en el VPS antes de levantar el stack.
#
# Uso:
#   chmod +x scripts/init_certs.sh
#   ./scripts/init_certs.sh tudominio.com admin@tudominio.com
# =============================================================

set -e

DOMAIN=${1?"Uso: $0 <dominio> <email>  Ejemplo: $0 tudominio.com admin@tudominio.com"}
EMAIL=${2?"Uso: $0 <dominio> <email>  Ejemplo: $0 tudominio.com admin@tudominio.com"}

COMPOSE_FILE="$(dirname "$0")/../docker-compose.yml"

echo "==> [1/4] Generando certificado auto-firmado temporal para que nginx arranque..."
mkdir -p "$(dirname "$0")/../nginx/dummy-certs"

docker run --rm -v "$(realpath "$(dirname "$0")/../nginx/dummy-certs")":/certs \
  alpine/openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout /certs/privkey.pem -out /certs/fullchain.pem \
  -subj "/CN=localhost" 2>/dev/null

# Precarga los volúmenes certbot con el cert dummy para que nginx no falle al arrancar
docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "" certbot \
  sh -c "mkdir -p /etc/letsencrypt/live/${DOMAIN} && \
         cp /dev/stdin /etc/letsencrypt/live/${DOMAIN}/fullchain.pem < /dev/null || true && \
         openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
           -keyout /etc/letsencrypt/live/${DOMAIN}/privkey.pem \
           -out /etc/letsencrypt/live/${DOMAIN}/fullchain.pem \
           -subj '/CN=localhost' 2>/dev/null"

echo "==> [2/4] Arrancando nginx con cert temporal..."
docker compose -f "$COMPOSE_FILE" up -d nginx

echo "==> [3/4] Obteniendo certificados reales de Let's Encrypt para:"
echo "          - ${DOMAIN}"
echo "          - www.${DOMAIN}"
echo "          - s3.${DOMAIN}"
echo "          - minio.${DOMAIN}"

docker compose -f "$COMPOSE_FILE" run --rm --entrypoint "" certbot \
  certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "${EMAIL}" \
    --agree-tos \
    --no-eff-email \
    -d "${DOMAIN}" \
    -d "www.${DOMAIN}" \
    -d "s3.${DOMAIN}" \
    -d "minio.${DOMAIN}"

echo "==> [4/4] Recargando nginx con los certificados reales..."
docker compose -f "$COMPOSE_FILE" exec odoo_nginx nginx -s reload

echo ""
echo "✓ Certificados obtenidos correctamente."
echo "  Ruta en el volumen: /etc/letsencrypt/live/${DOMAIN}/"
echo ""
echo "  Recuerda agregar el cron de renovación automática:"
echo "  crontab -e"
echo "  0 3 * * * /ruta/al/proyecto/infraestructura/scripts/renew_certs.sh >> /var/log/certbot-renew.log 2>&1"
