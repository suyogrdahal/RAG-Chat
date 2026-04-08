# Monorepo Deployment (EC2 + CodePipeline + CodeBuild + CodeDeploy)

## Runtime architecture
- Nginx listens on `80/443`.
- FastAPI runs on `127.0.0.1:8000` via `fastapi.service` (Uvicorn).
- Next.js runs on `127.0.0.1:3000` via `nextjs.service`.
- Widget static files are served from `/var/www/widget`, with `/widget.js` exposed by Nginx.

Nginx routes:
- `/api/` -> `http://127.0.0.1:8000/`
- `/` -> `http://127.0.0.1:3000`
- `/widget.js` -> `/var/www/widget/widget.js`

## Artifact packaging
`buildspec.yml` packages a CodeDeploy bundle containing:
- `backend/`
- `frontend/`
- `deploy/`
- `appspec.yml`
- `widget/` (built from `backend/public` when present, with fallback to repo `widget/`)

## CodeDeploy flow
`deploy/appspec.yml` hooks:
1. `ApplicationStop` -> `deploy/scripts/stop.sh`
2. CodeDeploy `Install` copies files to `/opt/app/current`
3. `AfterInstall` -> `deploy/scripts/install.sh`
4. `ApplicationStart` -> `deploy/scripts/start.sh`

`install.sh` order:
1. Ensure `/opt/app/current`, `/opt/app/shared`, `/var/www/widget`
2. Load/link env files for backend/frontend
3. Create/reuse venv at `/opt/app/venv`
4. Install backend requirements into venv
5. Run `alembic upgrade head`
6. Install frontend dependencies and build frontend
7. Install/reload systemd units
8. Sync widget static files
9. Install Nginx config

`start.sh`:
1. restart FastAPI
2. restart Next.js
3. validate and reload Nginx

## Environment files on EC2
Recommended:
- `/opt/app/shared/backend.env`
- `/opt/app/shared/frontend.env`

Legacy fallback:
- `/opt/app/shared/.env`

The deploy script symlinks:
- backend env -> `/opt/app/current/backend/.env`
- frontend env -> `/opt/app/current/frontend/.env.production.local`

## Safe env update process
1. Update files in `/opt/app/shared/` (do not commit secrets to git).
2. Redeploy through pipeline.
3. Verify services and Nginx:
- `systemctl status fastapi`
- `systemctl status nextjs`
- `nginx -t`
