#!/bin/bash
# Run this ONCE on first deployment to obtain the initial SSL certificate.
# After that, docker compose handles renewal automatically.

set -e

set -a
source .env
set +a

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "your-domain.com" ]; then
  echo "ERROR: Set DOMAIN in .env before running."
  exit 1
fi

if [ -z "$CERTBOT_EMAIL" ] || [ "$CERTBOT_EMAIL" = "your@email.com" ]; then
  echo "ERROR: Set CERTBOT_EMAIL in .env before running."
  exit 1
fi

echo "### Obtaining SSL certificate for $DOMAIN..."
docker compose run --rm \
  --publish 80:80 \
  --entrypoint "certbot certonly --standalone \
    --email $CERTBOT_EMAIL \
    -d $DOMAIN \
    --rsa-key-size 4096 \
    --agree-tos \
    --non-interactive" \
  certbot

echo "### Starting full stack..."
docker compose up -d --wait

echo "### Done! API is live at https://$DOMAIN"
