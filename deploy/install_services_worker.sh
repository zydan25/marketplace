#!/usr/bin/env bash
set -euo pipefail

APP_DIR="${1:-/home/root/projects/marketplace/backend}"
PYTHON="${APP_DIR}/venv/bin/python"
ENV_FILE="${APP_DIR}/.env"
UNIT_NAME="marketplace-services-worker.service"

if [[ ! -x "$PYTHON" ]]; then
  echo "ERROR: Python venv not found at $PYTHON" >&2
  exit 1
fi
if [[ ! -f "$ENV_FILE" ]]; then
  echo "ERROR: .env not found at $ENV_FILE" >&2
  exit 1
fi

sed \
  -e "s#^WorkingDirectory=.*#WorkingDirectory=${APP_DIR}#" \
  -e "s#^EnvironmentFile=.*#EnvironmentFile=${ENV_FILE}#" \
  -e "s#^ExecStart=.*#ExecStart=${PYTHON} manage.py process_service_tasks --loop --limit 10 --sleep 1 --error-sleep 3#" \
  deploy/systemd/${UNIT_NAME} > /etc/systemd/system/${UNIT_NAME}

systemctl daemon-reload
systemctl enable --now "${UNIT_NAME}"
systemctl --no-pager --full status "${UNIT_NAME}"
