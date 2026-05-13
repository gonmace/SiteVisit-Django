#!/bin/bash
# flush_demo.sh — elimina todos los datos de demostración
#
# Dev:   bash flush_demo.sh
# Prod:  bash flush_demo.sh          (detecta entorno automáticamente)
#        bash flush_demo.sh --force  (sin confirmación interactiva)
#
# En producción ejecuta el comando dentro del contenedor Django.

set -e

FORCE=""
[ "$1" = "--force" ] && FORCE="--force"

# Detectar entorno: si existe .env y DEBUG=False → producción
IS_PROD=false
if [ -f .env ]; then
    DEBUG_VAL=$(grep "^DEBUG=" .env | head -1 | cut -d'=' -f2-)
    [ "$DEBUG_VAL" = "False" ] && IS_PROD=true
fi

if $IS_PROD; then
    CONTAINER=$(docker compose ps -q django 2>/dev/null | head -1)
    if [ -z "$CONTAINER" ]; then
        echo "Error: contenedor Django no encontrado. ¿Está levantado? Ejecuta: make deploy"
        exit 1
    fi
    echo "▶ Ejecutando en contenedor de producción..."
    docker compose exec django python manage.py flush_demo_data $FORCE
else
    echo "▶ Ejecutando en entorno de desarrollo..."
    python manage.py flush_demo_data $FORCE
fi
