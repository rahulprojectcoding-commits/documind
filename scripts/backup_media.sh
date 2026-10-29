#!/usr/bin/env bash
set -Eeuo pipefail

if [[ -z "${MEDIA_BACKUP_S3_URI:-}" || "${MEDIA_BACKUP_S3_URI}" != s3://* ]]; then
    echo "Set MEDIA_BACKUP_S3_URI to a private S3 destination." >&2
    exit 2
fi

script_dir="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
project_dir="$(dirname -- "${script_dir}")"
compose_file="${COMPOSE_FILE:-${project_dir}/docker-compose.prod.yml}"
timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
destination="${MEDIA_BACKUP_S3_URI%/}/documind-media-${timestamp}.tar.gz"

docker compose -f "${compose_file}" exec -T web tar -C /app/media -czf - . | aws s3 cp - "${destination}" --sse AES256

echo "Media backup uploaded to ${destination}"
