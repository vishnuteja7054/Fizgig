"""Deploy the browser-native Fizgig workbench on Modal.

Builds the React bundle into the image and serves it from the same FastAPI
origin as the API.  The workspace Volume is separate from the source image so
datasets, jobs, caches, and outputs survive image rebuilds.

Deploy:
    modal deploy modal_app.py

For a one-off development URL, use ``modal serve modal_app.py`` instead.
Create the Volume once with ``modal volume create fizgig-workspace`` or let
the declaration create it during deployment.
"""

from pathlib import Path

import modal


ROOT = Path(__file__).resolve().parent
WORKSPACE = modal.Volume.from_name("fizgig-workspace", create_if_missing=True)
MODELS = modal.Volume.from_name("fizgig-models", create_if_missing=True)

IMAGE = (
    modal.Image.debian_slim(python_version="3.12")
    .apt_install("ffmpeg", "nodejs", "npm")
    .env({"DISABLE_CUDA": "1"})
    .pip_install_from_requirements(str(ROOT / "requirements.txt"))
    .pip_install_from_requirements(str(ROOT / "requirements-web.txt"))
    .add_local_dir(str(ROOT), remote_path="/opt/fizgig", copy=True)
    .run_commands("cd /opt/fizgig/web && npm install && npm run build")
)

app = modal.App("fizgig-browser")


@app.function(
    image=IMAGE,
    volumes={"/workspace": WORKSPACE, "/models": MODELS},
    # Change this to the GPU class selected for the mounted model set.
    # The API itself remains lazy and does not load weights at startup.
    gpu="L40S",
    timeout=24 * 60 * 60,
    scaledown_window=300,
    allow_concurrent_inputs=8,
    min_containers=0,
)
@modal.asgi_app()
def web():
    import os
    import sys

    sys.path.insert(0, "/opt/fizgig/src")
    os.environ["FIZGIG_WORKSPACE_ROOT"] = "/workspace"
    os.environ["FIZGIG_FRONTEND_DIST"] = "/opt/fizgig/web/dist"
    from fizgig.web.app import create_app

    return create_app("/workspace")
