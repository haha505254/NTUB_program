#!/bin/sh
set -o errexit
set -o pipefail
set -o nounset

if [ "${DJANGO_DB_SQLITE_PATH:-}" != "" ]; then
    db_dir="$(dirname "$DJANGO_DB_SQLITE_PATH")"
    mkdir -p "$db_dir"
fi

python manage.py migrate --noinput
python manage.py collectstatic --noinput

exec "$@"
