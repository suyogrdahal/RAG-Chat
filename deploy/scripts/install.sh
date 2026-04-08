#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="/opt/app/current"
SHARED_DIR="/opt/app/shared"
VENV_DIR="/opt/app/venv"
BACKEND_DIR="${APP_ROOT}/backend"
FRONTEND_DIR="${APP_ROOT}/frontend"
WIDGET_DST_DIR="/var/www/widget"

BACKEND_ENV_SHARED="${SHARED_DIR}/backend.env"
FRONTEND_ENV_SHARED="${SHARED_DIR}/frontend.env"
LEGACY_SHARED_ENV="${SHARED_DIR}/.env"

BACKEND_ENV_TARGET="${BACKEND_DIR}/.env"
FRONTEND_ENV_TARGET="${FRONTEND_DIR}/.env.production.local"

NGINX_CONF_SRC="${APP_ROOT}/deploy/nginx/app.conf"
NGINX_CONF_DST="/etc/nginx/conf.d/app.conf"

# Widget source defaults to backend/public; keeps compatibility with legacy /widget directory.
WIDGET_SRC_PRIMARY="${BACKEND_DIR}/public"
WIDGET_SRC_FALLBACK="${APP_ROOT}/widget"

mkdir -p "${APP_ROOT}" "${SHARED_DIR}" "${WIDGET_DST_DIR}"

backend_env_source=""
frontend_env_source=""

if [[ -f "${BACKEND_ENV_SHARED}" ]]; then
  backend_env_source="${BACKEND_ENV_SHARED}"
elif [[ -f "${LEGACY_SHARED_ENV}" ]]; then
  backend_env_source="${LEGACY_SHARED_ENV}"
fi

if [[ -f "${FRONTEND_ENV_SHARED}" ]]; then
  frontend_env_source="${FRONTEND_ENV_SHARED}"
elif [[ -f "${LEGACY_SHARED_ENV}" ]]; then
  frontend_env_source="${LEGACY_SHARED_ENV}"
fi

if [[ -n "${backend_env_source}" ]]; then
  ln -sfn "${backend_env_source}" "${BACKEND_ENV_TARGET}"
fi

if [[ -n "${frontend_env_source}" ]]; then
  ln -sfn "${frontend_env_source}" "${FRONTEND_ENV_TARGET}"
fi

if [[ ! -d "${VENV_DIR}" ]]; then
  python3 -m venv "${VENV_DIR}"
fi

if [[ -f "${BACKEND_DIR}/requirements.txt" ]]; then
  "${VENV_DIR}/bin/pip" install --upgrade pip
  "${VENV_DIR}/bin/pip" install -r "${BACKEND_DIR}/requirements.txt"
fi

if [[ -f "${BACKEND_DIR}/alembic.ini" ]]; then
  cd "${BACKEND_DIR}"
  "${VENV_DIR}/bin/alembic" -c alembic.ini upgrade head
fi

if [[ -d "${FRONTEND_DIR}" && -f "${FRONTEND_DIR}/package.json" ]]; then
  if id -u ec2-user >/dev/null 2>&1; then
    chown -R ec2-user:ec2-user "${FRONTEND_DIR}"
    runuser -u ec2-user -- bash -lc "cd '${FRONTEND_DIR}' && npm ci --no-audit --no-fund && npm run build"
  else
    cd "${FRONTEND_DIR}"
    npm ci --no-audit --no-fund
    npm run build
  fi
fi

if [[ -d "${WIDGET_SRC_PRIMARY}" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${WIDGET_SRC_PRIMARY}/" "${WIDGET_DST_DIR}/"
  else
    find "${WIDGET_DST_DIR}" -mindepth 1 -delete || true
    cp -a "${WIDGET_SRC_PRIMARY}/." "${WIDGET_DST_DIR}/"
  fi
elif [[ -d "${WIDGET_SRC_FALLBACK}" ]]; then
  if command -v rsync >/dev/null 2>&1; then
    rsync -a --delete "${WIDGET_SRC_FALLBACK}/" "${WIDGET_DST_DIR}/"
  else
    find "${WIDGET_DST_DIR}" -mindepth 1 -delete || true
    cp -a "${WIDGET_SRC_FALLBACK}/." "${WIDGET_DST_DIR}/"
  fi
fi

if [[ -f "${NGINX_CONF_SRC}" ]]; then
  install -m 0644 "${NGINX_CONF_SRC}" "${NGINX_CONF_DST}"
  rm -f /etc/nginx/conf.d/default.conf
fi

install -m 0644 "${APP_ROOT}/deploy/systemd/fastapi.service" /etc/systemd/system/fastapi.service
install -m 0644 "${APP_ROOT}/deploy/systemd/nextjs.service" /etc/systemd/system/nextjs.service

systemctl daemon-reload
