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
- `GET/POST /api/jobs`
- `GET /api/jobs/{id}`
- `GET /api/jobs/{id}/log`
- `POST /api/jobs/{id}/cancel`
- `POST /api/datasets/find-replace`
- `GET/PUT/DELETE /api/presets/{architecture}/{name}`
- `GET /api/presets/{architecture}`

This API is private-development infrastructure at this stage. Authentication,
workspace identity, upload limits, and job authorization are required before
public deployment.
