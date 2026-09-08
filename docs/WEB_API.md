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
- `GET /api/datasets/scan?folder=dataset/example`
- `GET /api/datasets/caption?item=dataset/example/photo.png`
- `PUT /api/datasets/caption`
- `POST /api/datasets/remove`
- `POST /api/datasets/find-replace`
- `GET/PUT/DELETE /api/presets/{architecture}/{name}`
- `GET /api/presets/{architecture}`

This API is private-development infrastructure at this stage. Authentication,
workspace identity, upload limits, and job authorization are required before
public deployment.
