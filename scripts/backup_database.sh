#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -z "${BACKUP_S3_URI:-}" || "${BACKUP_S3_URI}" != s3://* ]]; then
    echo "Set BACKUP_S3_URI to an S3 destination, e.g. s3://your-private-bucket/documind" >&2
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(dirname -- "${script_dir}")"
compose_file="${COMPOSE_FILE:-${project_dir}/docker-compose.prod.yml}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="${BACKUP_S3_URI%/}/documind-postgres-${timestamp}.sql.gz"

docker compose -f "${compose_file}" exec -T db sh -c \
    'exec pg_dump --no-owner --no-privileges -U "$POSTGRES_USER" "$POSTGRES_DB"' \
    | gzip \
    | aws s3 cp - "${destination}" --sse AES256

echo "Database backup uploaded to ${destination}"
