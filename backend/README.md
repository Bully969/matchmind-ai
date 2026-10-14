# Backend

FastAPI app. Local default is SQLite + `DATA_PROVIDER=demo` + deterministic chat template.

Useful endpoints: `/api/health`, `/api/providers`, `/api/competitions`, `/api/fixtures`, `/api/analyze`, `/api/chat`, `/api/predictions`, `/docs`.

Run from this directory: `uvicorn app.main:app --reload --host 127.0.0.1 --port 8000`.
