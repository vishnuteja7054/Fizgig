# Fizgig Web Frontend

This is the first browser-native shell for the migration. It is intentionally
small and honest: Start and Captions are connected to the first API slice;
model-heavy pages show a controlled-rollout state until their durable job and
GPU-session contracts exist.

## Development

From the repository root:

```bash
python -m pip install -r requirements-web.txt
PYTHONPATH=src uvicorn fizgig.web.app:app --reload --port 8000
```

In another terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the local FastAPI
process. Set `VITE_API_BASE_URL` when the frontend and API are deployed at
different origins.
