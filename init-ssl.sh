#!/bin/bash
# Run this ONCE on first deployment to obtain the initial SSL certificate.
# After that, docker compose handles renewal automatically.

set -e

DOMAIN="YOUR_DOMAIN"
EMAIL="YOUR_EMAIL"

if [ "$DOMAIN" = "YOUR_DOMAIN" ] || [ "$EMAIL" = "YOUR_EMAIL" ]; then
  echo "ERROR: Set DOMAIN and EMAIL at the top of this script before running."
  exit 1
fi

echo "### Creating dummy certificate so nginx can start..."
mkdir -p "./nginx/certbot/conf/live/$DOMAIN"
docker compose run --rm --entrypoint "openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
  -keyout /etc/letsencrypt/live/$DOMAIN/privkey.pem \
  -out /etc/letsencrypt/live/$DOMAIN/fullchain.pem \
  -subj /CN=localhost" certbot

echo "### Starting nginx with dummy certificate..."
docker compose up -d nginx
echo "Waiting for nginx..."
sleep 5

echo "### Removing dummy certificate..."
docker compose run --rm --entrypoint "rm -rf \
  /etc/letsencrypt/live/$DOMAIN \
  /etc/letsencrypt/archive/$DOMAIN \
  /etc/letsencrypt/renewal/$DOMAIN.conf" certbot

echo "### Requesting real certificate from Let's Encrypt..."
docker compose run --rm --entrypoint "certbot certonly --webroot \
  -w /var/www/certbot \
  --email $EMAIL \
  -d $DOMAIN \
  --rsa-key-size 4096 \
  --agree-tos \
  --non-interactive" certbot

echo "### Reloading nginx with real certificate..."
docker compose exec nginx nginx -s reload

echo "Done! SSL certificate obtained for $DOMAIN."
