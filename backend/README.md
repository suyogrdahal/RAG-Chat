# Backend (FastAPI) - Local Venv Workflow

This project uses a Windows virtual environment located at `backend\venv`.

## Setup (PowerShell)

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python --version
where python
python -m pip install -r requirements.txt
```

## Run the server (PowerShell)

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Health check:

```powershell
curl.exe http://127.0.0.1:8000/health
```

## How to validate Sprint 2 Task 1

1) Start the server:

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python --version
where python
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

2) Confirm `/auth/whoami` returns 401 without a token:

```powershell
curl.exe -i http://127.0.0.1:8000/auth/whoami
```

3) Mint a short-lived token and call `/auth/whoami`:

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
$token = python -m scripts.mint_token
curl.exe -i -H "Authorization: Bearer $token" http://127.0.0.1:8000/auth/whoami
```

4) Confirm `/health` returns 200:

```powershell
curl.exe -i http://127.0.0.1:8000/health
```

## Run tests

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python -m pytest -q
```

## Sprint 2 Task 2 (Database + Models)

Dev-only Postgres (Docker Compose):

```powershell
docker compose -f ../docker-compose.db.yml up -d
```

After configuring `.env`, run:

```powershell
python -m alembic upgrade head
python -m uvicorn app.main:app --reload
```

1) Configure database settings in `.env` (example for local Postgres):

```powershell
cd C:\Project\RAG-Chat\backend
Copy-Item .env.example .env
notepad .env
```

2) Run migrations:

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python -m alembic upgrade head
```

Smoke test (no auth, no API):

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python -m scripts.smoke_db
```

3) Start the server:

```powershell
cd C:\Project\RAG-Chat\backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

4) Debug endpoints (no auth):

Create org:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/debug/orgs `
  -H "Content-Type: application/json" `
  -d "{\"name\":\"Acme\",\"slug\":\"acme\"}"
```

Read org:

```powershell
curl.exe -i http://127.0.0.1:8000/debug/orgs/<org_id>
```

Create user:

```powershell
curl.exe -i -X POST http://127.0.0.1:8000/debug/users `
  -H "Content-Type: application/json" `
  -d "{\"org_id\":\"<org_id>\",\"email\":\"admin@acme.test\"}"
```

Read user:

```powershell
curl.exe -i http://127.0.0.1:8000/debug/users/<user_id>
```
