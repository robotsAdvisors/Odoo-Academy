#!/bin/bash
# =============================================================
# init_certs.sh — Obtención inicial de certificados Let's Encrypt
#
# Genera UN CERTIFICADO POR SUBDOMINIO, porque nginx referencia una
# ruta ssl_certificate distinta para cada uno:
#   /etc/letsencrypt/live/<sub>.<dominio>/
#
# Requisito previo: cada subdominio debe tener ya su registro A
# apuntando a este servidor. Si no, certbot falla la validación.
#
# Uso:
#   chmod +x scripts/init_certs.sh
#   ./scripts/init_certs.sh robotsconsultant.net admin@robotsconsultant.net
#
# Por defecto solo pide el de 'cursos'. Para añadir MinIO cuando sus
# registros A existan (y tras renombrar nginx/minio.conf.disabled):
#   ./scripts/init_certs.sh robotsconsultant.net admin@... cursos s3 minio
#
# Prueba sin gastar cuota de Let's Encrypt (5 fallos/hora por dominio):
#   STAGING=1 ./scripts/init_certs.sh robotsconsultant.net admin@...
# =============================================================

set -euo pipefail

DOMAIN=${1?"Uso: $0 <dominio-base> <email> [subdominio...]"}
EMAIL=${2?"Uso: $0 <dominio-base> <email> [subdominio...]"}
shift 2
SUBS=("${@:-cursos}")
STAGING=${STAGING:-0}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="${SCRIPT_DIR}/../docker-compose.yml"
COMPOSE=(docker compose -f "$COMPOSE_FILE")

FQDNS=()
for s in "${SUBS[@]}"; do
    FQDNS+=("${s}.${DOMAIN}")
done

STAGING_ARG=()
if [ "$STAGING" != "0" ]; then
    echo "!! MODO STAGING: los certificados NO serán de confianza. Solo para probar el flujo."
    STAGING_ARG=(--staging)
fi

echo "Se solicitarán certificados para: ${FQDNS[*]}"
echo ""

# -------------------------------------------------------------
echo "==> [1/5] Comprobando que el DNS apunta a este servidor..."
MY_IP="$(curl -fsS --max-time 15 https://api.ipify.org || echo '')"
for fqdn in "${FQDNS[@]}"; do
    resolved="$(getent hosts "$fqdn" | awk '{print $1}' | head -n1 || true)"
    if [ -z "$resolved" ]; then
        echo "    ERROR: ${fqdn} no resuelve. Crea el registro A antes de continuar."
        exit 1
    fi
    if [ -n "$MY_IP" ] && [ "$resolved" != "$MY_IP" ]; then
        echo "    ERROR: ${fqdn} -> ${resolved}, pero la IP pública es ${MY_IP}."
        echo "           Let's Encrypt validará contra ${resolved}, no contra este servidor."
        echo "           (Si usas Cloudflare en modo proxy, ponlo en nube gris mientras validas.)"
        exit 1
    fi
    echo "    OK: ${fqdn} -> ${resolved}"
done

# -------------------------------------------------------------
echo "==> [2/5] Creando certificados auto-firmados temporales..."
# Sin esto nginx aborta al arrancar: no puede cargar un ssl_certificate
# que no existe, y sin nginx no hay webroot para el challenge ACME.
for fqdn in "${FQDNS[@]}"; do
    "${COMPOSE[@]}" run --rm --entrypoint sh certbot -c "
        mkdir -p /etc/letsencrypt/live/${fqdn} &&
        openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
          -keyout /etc/letsencrypt/live/${fqdn}/privkey.pem \
          -out    /etc/letsencrypt/live/${fqdn}/fullchain.pem \
          -subj '/CN=${fqdn}' 2>/dev/null" >/dev/null
    echo "    dummy creado: ${fqdn}"
done

# -------------------------------------------------------------
echo "==> [3/5] Arrancando nginx con los certs temporales..."
"${COMPOSE[@]}" up -d nginx
sleep 3
if ! "${COMPOSE[@]}" exec -T nginx nginx -t; then
    echo "    ERROR: la configuración de nginx no es válida. Abortando."
    exit 1
fi

# -------------------------------------------------------------
echo "==> [4/5] Solicitando certificados reales a Let's Encrypt..."
for fqdn in "${FQDNS[@]}"; do
    echo "    --- ${fqdn} ---"

    # Borrar el dummy: si no, certbot lo detecta como cert existente
    # y entra en el flujo de renovación en lugar de emitir uno nuevo.
    "${COMPOSE[@]}" run --rm --entrypoint sh certbot -c "
        rm -rf /etc/letsencrypt/live/${fqdn} \
               /etc/letsencrypt/archive/${fqdn} \
               /etc/letsencrypt/renewal/${fqdn}.conf" >/dev/null

    "${COMPOSE[@]}" run --rm --entrypoint certbot certbot \
        certonly \
        --webroot \
        --webroot-path=/var/www/certbot \
        --email "${EMAIL}" \
        --agree-tos \
        --no-eff-email \
        --non-interactive \
        "${STAGING_ARG[@]}" \
        -d "${fqdn}"
done

# -------------------------------------------------------------
echo "==> [5/5] Recargando nginx con los certificados reales..."
# El servicio se llama 'nginx' en docker-compose.yml
"${COMPOSE[@]}" exec -T nginx nginx -s reload

echo ""
echo "✓ Certificados obtenidos:"
for fqdn in "${FQDNS[@]}"; do
    echo "    /etc/letsencrypt/live/${fqdn}/"
done
echo ""
echo "  Levanta el resto del stack:"
echo "    docker compose -f ${COMPOSE_FILE} up -d"
echo ""
echo "  Y añade la renovación automática al crontab (crontab -e):"
echo "    0 3 * * * ${SCRIPT_DIR}/renew_certs.sh >> /var/log/certbot-renew.log 2>&1"
