#!/usr/bin/env bash
set -euo pipefail

if systemctl list-unit-files | grep -q '^fastapi.service'; then
  systemctl stop fastapi.service || true
fi

if systemctl list-unit-files | grep -q '^nextjs.service'; then
  systemctl stop nextjs.service || true
fi
