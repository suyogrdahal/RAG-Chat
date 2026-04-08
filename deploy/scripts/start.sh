#!/usr/bin/env bash
set -euo pipefail

systemctl daemon-reload

for svc in fastapi.service nextjs.service; do
  if systemctl list-unit-files --type=service | grep -q "^${svc}"; then
    systemctl enable "${svc}" >/dev/null 2>&1 || true
    systemctl restart "${svc}"
  fi
done

nginx -t
systemctl enable nginx >/dev/null 2>&1 || true
systemctl reload nginx || systemctl restart nginx
