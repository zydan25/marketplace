#!/usr/bin/env bash
set -e

python manage.py migrate --noinput
python scripts/bootstrap_render_admin.py
gunicorn --bind 0.0.0.0:${PORT} config.wsgi:application
