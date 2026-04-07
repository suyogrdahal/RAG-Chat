#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/app/current"
SHARED_ENV="/opt/app/shared/.env"
VENV_DIR="/opt/app/venv"
BACKEND_DIR="${APP_ROOT}/backend"
FRONTEND_DIR="${APP_ROOT}/frontend"
WIDGET_DIR="${APP_ROOT}/widget"
NGINX_CONF_SRC="${APP_ROOT}/deploy/nginx/app.conf"
NGINX_CONF_DST="/etc/nginx/conf.d/app.conf"

mkdir -p /opt/app/current /opt/app/shared /var/www/widget

if [[ -f "${SHARED_ENV}" ]]; then
  set -a
  # shellcheck disable=SC1090
  source "${SHARED_ENV}"
  set +a
fi

if [[ -d "${BACKEND_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
  "${VENV_DIR}/bin/pip" install --upgrade pip
  if [[ -f "${BACKEND_DIR}/requirements.txt" ]]; then
    "${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
  fi
fi

if [[ -d "${FRONTEND_DIR}" ]]; then
  cd "${FRONTEND_DIR}"
  npm ci
  npm run build
fi

if [[ -f "${WIDGET_DIR}/widget.js" ]]; then
  install -m 0644 "${WIDGET_DIR}/widget.js" /var/www/widget/widget.js
elif [[ -d "${WIDGET_DIR}" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${WIDGET_DIR}/" /var/www/widget/
  else
    rm -rf /var/www/widget/*
    cp -R "${WIDGET_DIR}/." /var/www/widget/
  fi
fi

if [[ -f "${NGINX_CONF_SRC}" ]]; then
  install -m 0644 "${NGINX_CONF_SRC}" "${NGINX_CONF_DST}"
  rm -f /etc/nginx/conf.d/default.conf
fi

install -m 0644 "${APP_ROOT}/deploy/systemd/fastapi.service" /etc/systemd/system/fastapi.service
install -m 0644 "${APP_ROOT}/deploy/systemd/nextjs.service" /etc/systemd/system/nextjs.service

systemctl daemon-reload
