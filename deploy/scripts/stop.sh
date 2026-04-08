#!/usr/bin/env bash
set -euo pipefail

for svc in fastapi.service nextjs.service; do
  if systemctl list-unit-files --type=service | grep -q "^${svc}"; then
    systemctl stop "${svc}" || true
  fi
done
