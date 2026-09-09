# Fizgig Web Frontend

This is the first browser-native shell for the migration. It is intentionally
small and honest: Start and Captions are connected to the first API slice;
model-heavy pages show a controlled-rollout state until their durable job and
GPU-session contracts exist.

## Development

Run the API commands from the repository root (the directory containing
`requirements-web.txt` and `src/`):

```bash
cd /path/to/Fizgig
source web/venv/bin/activate  # or activate your existing project venv
python -m pip install -r requirements-web.txt
python -m uvicorn --app-dir src fizgig.web.app:app --reload --port 8000
```

Do not run the API command from inside `web/`: the Python package is in the
repository-level `src/` directory, not `web/src/`. Using `python -m uvicorn`
also ensures the server comes from the active virtual environment.

The browser workbench includes workspace/dataset import and captions, image
prep, samples, training configuration and durable jobs, presets, Profiler,
Extract, metadata inspection, Repair Studio bake/render jobs, LoRA
Explorer/Royale catalogs and render jobs, and workspace artifact downloads.
Model-heavy actions run on the server/worker; the browser never loads model
weights or assumes access to the server filesystem.

Use the Jobs page to reconnect to persisted operations after a browser refresh;
the API polls the workspace-backed job records independently of the page that
started them.

In another terminal:

```bash
cd web
npm install
npm run dev
```

Open `http://localhost:5173`. Vite proxies `/api` to the local FastAPI
process. Set `VITE_API_BASE_URL` when the frontend and API are deployed at
different origins.
