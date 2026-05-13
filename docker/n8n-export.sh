#!/bin/bash
# Exporta workflows y credenciales de n8n dev al repositorio.
# Uso: make n8n-export

set -e

WORKFLOWS_DIR="./n8n/workflows"
CREDENTIALS_DIR="./n8n/credentials"

mkdir -p "$WORKFLOWS_DIR" "$CREDENTIALS_DIR"

echo "▶ Exportando workflows..."
docker compose -f docker-compose.dev.yml exec n8n \
    mkdir -p /home/node/.n8n/exports/workflows/
docker compose -f docker-compose.dev.yml exec n8n \
    n8n export:workflow --all --separate --output=/home/node/.n8n/exports/workflows/

docker compose -f docker-compose.dev.yml cp \
    n8n:/home/node/.n8n/exports/workflows/. "$WORKFLOWS_DIR/"

echo "▶ Exportando credenciales..."
docker compose -f docker-compose.dev.yml exec n8n \
    mkdir -p /home/node/.n8n/exports/credentials/
docker compose -f docker-compose.dev.yml exec n8n \
    n8n export:credentials --all --separate --output=/home/node/.n8n/exports/credentials/

docker compose -f docker-compose.dev.yml cp \
    n8n:/home/node/.n8n/exports/credentials/. "$CREDENTIALS_DIR/"

echo ""
echo "✓ Exportado en:"
echo "  Workflows:    $WORKFLOWS_DIR/"
echo "  Credenciales: $CREDENTIALS_DIR/"
echo ""
echo "  Siguiente: git add n8n/ && git commit -m 'chore: exportar n8n' && git push"
