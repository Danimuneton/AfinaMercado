#!/bin/sh
# Arranque del contenedor de Django: migraciones, superusuario opcional y gunicorn.
set -e

python manage.py migrate --noinput

if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput \
    --username "$DJANGO_SUPERUSER_USERNAME" \
    --email "${DJANGO_SUPERUSER_EMAIL:-admin@afinamercado.co}" 2>/dev/null \
    && echo "Superusuario '$DJANGO_SUPERUSER_USERNAME' creado" \
    || echo "Superusuario '$DJANGO_SUPERUSER_USERNAME' ya existe"
fi

exec gunicorn afinamercado_project.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-2}" \
  --timeout 60 \
  --access-logfile -
