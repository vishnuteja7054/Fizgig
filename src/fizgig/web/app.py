"""Minimal browser API built on the frontend-neutral application services.

This is intentionally a thin HTTP adapter.  It owns request/response shapes
and HTTP status codes; filesystem safety and data semantics live in
``fizgig.app`` so the desktop and browser paths can share them.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

try:
    from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile
    from pydantic import BaseModel, Field
except ImportError as exc:  # pragma: no cover - gives a useful startup error
    raise RuntimeError(
        "The browser API requires the optional web dependencies. "
        "Install with: pip install -r requirements-web.txt"
    ) from exc

from fizgig import __version__ as FIZGIG_VERSION
from fizgig.app.dataset import DatasetService
from fizgig.app.image_prep import ImagePrepService
from fizgig.app.jobs import JobService
from fizgig.app.workspace import WorkspaceStateError, WorkspaceStateService
from fizgig.app.training_config import (
    DatasetConfigRequest,
    TrainingConfigError,
    TrainingConfigService,
)
from fizgig.app.presets import (
    PresetError,
    PresetExistsError,
    PresetNotFoundError,
    PresetRepository,
)


class DatasetItemResponse(BaseModel):
    relative_path: str
    kind: str
    caption_relative_path: str
    has_caption: bool


class DatasetScanResponse(BaseModel):
    folder: str
    items: list[DatasetItemResponse]


class DatasetImportResponse(BaseModel):
    folder: str
    imported: list[str]
    skipped: list[str]


class CaptionResponse(BaseModel):
    item: str
    text: str


class CaptionUpdateRequest(BaseModel):
    item: str = Field(min_length=1)
    text: str


class RemoveItemRequest(BaseModel):
    item: str = Field(min_length=1)


class FindReplaceRequest(BaseModel):
    folder: str = Field(min_length=1)
    find: str = Field(min_length=1)
    replace: str
    apply: bool = False


class ImagePrepRequest(BaseModel):
    folder: str = Field(min_length=1)
    target_megapixels: float = Field(default=1.0, gt=0, le=100)
    replace_originals: bool = False


class TrainingDatasetConfigRequest(BaseModel):
    name: str = Field(default="Fizgig_train", min_length=1)
    folder: str = Field(default="dataset", min_length=1)
    target_megapixels: float = Field(default=0.25, gt=0, le=100)
    batch_size: int = Field(default=1, ge=1, le=1024)
    caption_extension: str = ".txt"
    enable_bucket: bool = True
    bucket_no_upscale: bool = True
    cache_root: str = Field(default="cache", min_length=1)


class JobCreateRequest(BaseModel):
    kind: str = Field(min_length=1)
    payload: dict[str, Any] = Field(default_factory=dict)


class PresetSaveRequest(BaseModel):
    values: dict[str, Any]
    overwrite: bool = False


class HealthResponse(BaseModel):
    status: str
    fizgig_version: str
    api_version: str


class WorkspaceStateUpdateRequest(BaseModel):
    values: dict[str, Any]


def _default_workspace_root() -> Path:
    configured = os.environ.get("FIZGIG_WORKSPACE_ROOT")
    if configured:
        return Path(configured).expanduser()
    # Source checkout fallback.  Modal should always set the environment
    # variable to a mounted Volume rather than relying on this default.
    return Path(__file__).resolve().parents[3]


def create_app(workspace_root: str | os.PathLike[str] | None = None) -> FastAPI:
    """Create an API app for one isolated Fizgig workspace."""

    root = Path(workspace_root or _default_workspace_root()).expanduser().resolve()
    dataset = DatasetService(root)
    image_prep = ImagePrepService(root)
    workspace_state = WorkspaceStateService(root)
    training_config = TrainingConfigService(root)
    jobs = JobService(root)
    presets = PresetRepository(root)

    app = FastAPI(
        title="Fizgig Browser API",
        version="0.1.0",
        description="Browser-safe control plane for the Fizgig workbench.",
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", fizgig_version=FIZGIG_VERSION, api_version="0.1.0")

    @app.get("/api/workspace/state")
    def get_workspace_state() -> dict[str, Any]:
        return {"values": workspace_state.load()}

    @app.patch("/api/workspace/state")
    def update_workspace_state(request: WorkspaceStateUpdateRequest) -> dict[str, Any]:
        try:
            return {"values": workspace_state.update(request.values)}
        except WorkspaceStateError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/datasets/scan", response_model=DatasetScanResponse)
    def scan_dataset(
        folder: str = Query(min_length=1),
        include_video: bool = True,
        include_audio: bool = True,
    ) -> DatasetScanResponse:
        try:
            items = dataset.scan(folder, include_video=include_video, include_audio=include_audio)
        except (ValueError, NotADirectoryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DatasetScanResponse(
            folder=folder,
            items=[DatasetItemResponse(**item.__dict__) for item in items],
        )

    @app.get("/api/datasets/caption", response_model=CaptionResponse)
    def read_caption(item: str = Query(min_length=1)) -> CaptionResponse:
        try:
            text = dataset.read_caption(item)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return CaptionResponse(item=item, text=text)

    @app.post("/api/datasets/import", response_model=DatasetImportResponse)
    def import_dataset(
        folder: str = Form(min_length=1),
        files: list[UploadFile] = File(...),
    ) -> DatasetImportResponse:
        imported: list[str] = []
        skipped: list[str] = []
        for upload in files:
            filename = upload.filename or ""
            if not DatasetService.is_importable_filename(filename):
                skipped.append(filename or "(unnamed file)")
                continue
            try:
                imported.append(dataset.import_file(folder, filename, upload.file))
            except FileExistsError:
                skipped.append(filename)
            except (ValueError, NotADirectoryError) as exc:
                raise HTTPException(status_code=400, detail=str(exc)) from exc
        return DatasetImportResponse(folder=folder, imported=imported, skipped=skipped)

    @app.put("/api/datasets/caption", response_model=CaptionResponse)
    def write_caption(request: CaptionUpdateRequest) -> CaptionResponse:
        try:
            dataset.write_caption(request.item, request.text)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return CaptionResponse(item=request.item, text=request.text.strip())

    @app.post("/api/datasets/remove")
    def remove_dataset_item(request: RemoveItemRequest) -> dict[str, str | None]:
        try:
            media, caption = dataset.move_to_removed(request.item)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except FileNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        return {"media_relative_path": media, "caption_relative_path": caption}

    @app.post("/api/image-prep/resize-only")
    def resize_only(request: ImagePrepRequest) -> dict[str, Any]:
        try:
            return image_prep.resize_only(
                request.folder,
                request.target_megapixels,
                replace_originals=request.replace_originals,
            ).as_dict()
        except (ValueError, NotADirectoryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/training/dataset-config")
    def write_training_dataset_config(request: TrainingDatasetConfigRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            output, content = training_config.build(DatasetConfigRequest(**values))
        except (TrainingConfigError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {
            "config_relative_path": output.relative_to(root).as_posix(),
            "content": content,
        }

    @app.get("/api/jobs")
    def list_jobs(limit: int = Query(default=50, ge=1, le=200)) -> dict[str, Any]:
        return {"jobs": [record.as_dict() for record in jobs.list(limit=limit)]}

    @app.get("/api/jobs/{job_id}")
    def get_job(job_id: str) -> dict[str, Any]:
        try:
            return jobs.get(job_id).as_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/jobs/{job_id}/cancel")
    def cancel_job(job_id: str) -> dict[str, Any]:
        try:
            return jobs.cancel(job_id).as_dict()
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except ValueError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.post("/api/jobs")
    def create_job(request: JobCreateRequest) -> dict[str, Any]:
        if request.kind != "image_prep.resize_only":
            raise HTTPException(status_code=400, detail=f"unsupported job kind: {request.kind}")
        try:
            prep_request = ImagePrepRequest(**request.payload)
        except Exception as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def run_resize(context, payload):
            context.update(progress=5, message="Preparing images")
            result = image_prep.resize_only(
                payload["folder"],
                payload.get("target_megapixels", 1.0),
                replace_originals=payload.get("replace_originals", False),
            )
            context.update(progress=100, message="Image preparation complete")
            return result.as_dict()

        return jobs.create(request.kind, prep_request.model_dump() if hasattr(prep_request, "model_dump") else prep_request.dict(), run_resize).as_dict()

    @app.post("/api/datasets/find-replace")
    def find_replace(request: FindReplaceRequest) -> dict[str, Any]:
        try:
            results = dataset.find_replace(
                request.folder, request.find, request.replace, apply=request.apply
            )
        except (ValueError, NotADirectoryError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"applied": request.apply, "count": len(results), "results": results}

    @app.get("/api/presets/{architecture}")
    def list_presets(architecture: str) -> dict[str, Any]:
        try:
            return {"architecture": architecture, "names": presets.list(architecture)}
        except PresetError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/presets/{architecture}/{name}")
    def load_preset(architecture: str, name: str) -> dict[str, Any]:
        try:
            return presets.load(architecture, name)
        except PresetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PresetError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.put("/api/presets/{architecture}/{name}")
    def save_preset(architecture: str, name: str, request: PresetSaveRequest) -> dict[str, Any]:
        try:
            presets.save(architecture, name, request.values, overwrite=request.overwrite)
        except PresetExistsError as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        except PresetError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"architecture": architecture, "name": name, "values": request.values}

    @app.delete("/api/presets/{architecture}/{name}")
    def delete_preset(architecture: str, name: str) -> dict[str, str]:
        try:
            presets.delete(architecture, name)
        except PresetNotFoundError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except PresetError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"architecture": architecture, "name": name}

    return app


app = create_app()
