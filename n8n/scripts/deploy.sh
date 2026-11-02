#!/usr/bin/env bash
set -euo pipefail

# Ejecutar desde la raíz del checkout del runner self-hosted.
WORKFLOW_ID=25pZ9DqIHtB4KqOY
WORKFLOW_FILE=/workflows/automatic-plan.json
BACKUP_DIR="$(realpath -m "../n8n-backups/${BACKUP_NAME:?Falta BACKUP_NAME}")"
N8N_CONTAINER="$(docker compose ps -q n8n)"

if [ -z "$N8N_CONTAINER" ]; then
  echo "::error::El contenedor de n8n debe existir antes de desplegar el workflow."
  exit 1
fi

umask 077
mkdir -p "$BACKUP_DIR"

# La CLI escribe directamente en SQLite: detener n8n antes de copiar y de
# importar/publicar, para evitar carreras y respaldos inconsistentes.
docker compose stop n8n
restart_n8n() {
  docker compose up -d --no-deps n8n
}
trap restart_n8n EXIT

docker cp "$N8N_CONTAINER:/home/node/.n8n" "$BACKUP_DIR/"
echo "Respaldo de n8n guardado fuera del checkout en $BACKUP_DIR"

docker compose run --rm --no-deps n8n import:workflow --input="$WORKFLOW_FILE"
docker compose run --rm --no-deps n8n publish:workflow --id="$WORKFLOW_ID"
docker compose run --rm --no-deps n8n export:workflow --id="$WORKFLOW_ID" --published --output=/dev/null

echo "Workflow $WORKFLOW_ID importado y publicado."
