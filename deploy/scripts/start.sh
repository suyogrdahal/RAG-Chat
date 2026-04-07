#!/usr/bin/env bash
set -euo pipefail

systemctl daemon-reload
systemctl enable fastapi.service
systemctl restart fastapi.service

systemctl enable nextjs.service
systemctl restart nextjs.service

nginx -t
systemctl enable nginx
systemctl reload nginx || systemctl restart nginx
