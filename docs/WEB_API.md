# Fizgig Browser API

The first browser API slice exposes workspace-local dataset and custom-preset
operations. It is intentionally separate from the Tkinter entry point and does
not load model weights.

Install the optional API dependencies:

```bash
python -m pip install -r requirements-web.txt
```

Run from a source checkout:

```bash
PYTHONPATH=src uvicorn fizgig.web.app:app --host 127.0.0.1 --port 8000
```

Set `FIZGIG_WORKSPACE_ROOT` to a mounted workspace before starting the server
in Modal. The default is only intended for local source-checkout development.

Initial endpoints:

- `GET /api/health`
- `GET/PATCH /api/workspace/state`
- `GET /api/datasets/scan?folder=dataset/example`
- `GET /api/datasets/caption?item=dataset/example/photo.png`
- `PUT /api/datasets/caption`
- `POST /api/datasets/remove`
- `POST /api/datasets/import` (browser folder upload)
- `POST /api/image-prep/resize-only`
- `POST /api/training/dataset-config`
- `POST /api/training/command-preview` (validate and preview a Klein/Krea 2/MiniMax command)
- `POST /api/training/start` (start a persistent model-training job)
- `POST /api/samples/prompts`
- `POST/DELETE /api/samples/override`
- `POST /api/workbench/profile/{preview,start}`
- `POST /api/workbench/extract/{preview,start}`
- `GET /api/metadata/inspect?path=...`
- `GET /api/lora/explorer?folder=...`
- `GET /api/lora/royale?folder=...`
- `GET /api/repair/default-state?family=...`
- `POST /api/repair/bake/{preview,start}`
- `POST /api/repair/render/{preview,start}` (GPU preview job; model paths are server-side)
- `GET/POST /api/jobs`
- `GET /api/jobs/{id}`
- `GET /api/jobs/{id}/log`
- `POST /api/jobs/{id}/cancel`
- `GET /api/artifacts/download?path=...`
- `POST /api/datasets/find-replace`
- `GET/PUT/DELETE /api/presets/{architecture}/{name}`
- `GET /api/presets/{architecture}`

This API is private-development infrastructure at this stage. Authentication,
workspace identity, upload limits, and job authorization are required before
public deployment.

## Modal deployment

`modal_app.py` installs the full model requirements plus web requirements,
builds `web/`, serves the React bundle and FastAPI API from one origin, and
mounts persistent workspace/model Volumes at `/workspace` and `/models`:

```bash
modal deploy modal_app.py
```

The example uses an L40S worker because Repair/Explorer/Royale and training are
GPU-backed. Populate the `fizgig-models` Volume at the paths used in
Preferences before starting model jobs. Adjust the GPU class if needed. Do not expose the URL
publicly until authentication and workspace isolation are added.

Optional bearer authentication is available for deployments: set
`FIZGIG_API_TOKEN` on the API process and build the frontend with the matching
`VITE_API_TOKEN`. The health endpoint remains public for probes; other API
routes require `Authorization: Bearer <token>`. Leave both variables unset for
local development.
