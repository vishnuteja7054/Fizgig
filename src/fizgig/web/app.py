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


class PresetSaveRequest(BaseModel):
    values: dict[str, Any]
    overwrite: bool = False


class HealthResponse(BaseModel):
    status: str
    fizgig_version: str
    api_version: str


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
    presets = PresetRepository(root)

    app = FastAPI(
        title="Fizgig Browser API",
        version="0.1.0",
        description="Browser-safe control plane for the Fizgig workbench.",
    )

    @app.get("/api/health", response_model=HealthResponse)
    def health() -> HealthResponse:
        return HealthResponse(status="ok", fizgig_version=FIZGIG_VERSION, api_version="0.1.0")

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
