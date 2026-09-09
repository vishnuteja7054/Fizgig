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
    from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
    from fastapi.staticfiles import StaticFiles
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
from fizgig.app.catalog import CatalogError, LoraCatalogService
from fizgig.app.metadata import MetadataError, MetadataService
from fizgig.app.samples import SampleError, SampleService
from fizgig.app.workbench import (
    ExtractRequest,
    ProfileRequest,
    WorkbenchCommandService,
    WorkbenchError,
    run_workbench_job,
)
from fizgig.app.training import TrainingCommandService, TrainingLaunchError, run_training_job
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
from fizgig.app.repair import RepairError, RepairService
from fizgig.app.state import WorkspacePaths


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


class TrainingLaunchRequest(BaseModel):
    architecture: str = Field(min_length=1)
    dataset_config: str = Field(min_length=1)
    dit: str = Field(min_length=1)
    output_dir: str = Field(default="output_loras", min_length=1)
    output_name: str = Field(default="fizgig_lora", min_length=1)
    vae: str = ""
    text_encoder: str = ""
    network_dim: int = Field(default=16, ge=1, le=65536)
    network_alpha: float = Field(default=16, gt=0)
    learning_rate: float = Field(default=1e-4, gt=0)
    max_train_epochs: int = Field(default=10, ge=1)
    save_every_n_epochs: int = Field(default=0, ge=0)
    seed: int = 42
    blocks_to_swap: int | str = 0
    optimizer_type: str = "adamw8bit"
    optimizer_args: str = ""
    gradient_checkpointing: bool = True
    gradient_accumulation_steps: int = Field(default=1, ge=1)
    max_grad_norm: float = Field(default=1.0, ge=0)
    network_type: str = "lora"
    lokr_factor: int = Field(default=8, ge=1)
    lora_lr_ratio: int = Field(default=1, ge=1)
    save_state: bool = True
    save_state_on_train_end: bool = True
    keep_last_n_states: int = Field(default=2, ge=1)
    resume: str = ""
    quantize_4bit: bool = False
    quant_int8: str = ""
    base_quant: str = "auto"
    use_fp8_base: bool = True
    discrete_flow_shift: float = 2.5
    sample_prompts: str = ""
    sample_every_n_epochs: int = Field(default=0, ge=0)
    sample_at_first: bool = False
    sample_width: int = Field(default=512, ge=1)
    sample_height: int = Field(default=512, ge=1)
    sample_steps: int = Field(default=8, ge=1)
    sample_cfg_scale: float = Field(default=1.0, gt=0)
    sample_negative: str = ""
    sample_seed: int = 42
    prepare_cache: bool = True
    extra_args: list[str] = Field(default_factory=list)


class SamplePromptsRequest(BaseModel):
    name: str = "prompts.txt"
    text: str = ""
    folder: str = "samples"


class SampleOverrideRequest(BaseModel):
    output_dir: str = Field(min_length=1)
    prompt: str = ""
    seed: int = 1234
    width: int = 768
    height: int = 768
    ref_image: str = ""


class ProfileToolRequest(BaseModel):
    lora: str = Field(min_length=1)
    output: str = "out/profile.html"
    krea2: bool = True
    dit: str = ""
    vae: str = ""
    text_encoder: str = ""
    num_samples: int = Field(default=8, ge=1)
    num_bins: int = Field(default=5, ge=1)
    width: int = Field(default=1024, ge=16)
    height: int = Field(default=1024, ge=16)
    prompt: str = ""
    blocks_to_swap: int = Field(default=12, ge=0)
    seed: int | None = None


class ExtractToolRequest(BaseModel):
    source: str = Field(min_length=1)
    output: str = "output_loras/extracted.safetensors"
    samples: int = Field(default=0, ge=0)
    rank: int = Field(default=2, ge=1)
    blocks: str = "all"
    custom_blocks: str = ""
    timesteps: str = "all"
    prompt: str = "a photo"
    width: int = Field(default=1024, ge=16)
    height: int = Field(default=1024, ge=16)
    multiplier: float = 1.0
    seed: int | None = None
    dit: str = ""
    vae: str = ""
    text_encoder: str = ""


class RepairBakeRequest(BaseModel):
    primary: str = Field(min_length=1)
    output: str = Field(min_length=1)
    state: dict[str, Any]
    donor: str = ""


class RepairRenderRequest(RepairBakeRequest):
    family: str = "klein"
    dit: str = Field(min_length=1)
    vae: str = Field(min_length=1)
    text_encoder: str = Field(min_length=1)
    device: str = "cuda"
    blocks_to_swap: int = Field(default=0, ge=0)


class ExplorerRenderRequest(BaseModel):
    family: str = "klein"
    primary: str = Field(min_length=1)
    donor: str = ""
    output_dir: str = "out/explorer"
    state: dict[str, Any]
    dit: str = Field(min_length=1)
    vae: str = Field(min_length=1)
    text_encoder: str = Field(min_length=1)
    device: str = "cuda"
    blocks_to_swap: int = Field(default=0, ge=0)
    variants: int = Field(default=4, ge=1, le=8)
    intensity: float = Field(default=0.5, ge=0, le=1)
    structure: float = Field(default=1.0, ge=0, le=1)


class RoyaleRenderRequest(BaseModel):
    family: str = "klein"
    folder: str = "output_loras"
    output_dir: str = "out/royale"
    dit: str = Field(min_length=1)
    vae: str = Field(min_length=1)
    text_encoder: str = Field(min_length=1)
    prompt: str = ""
    seed: int = 42
    width: int = Field(default=512, ge=16)
    height: int = Field(default=512, ge=16)
    device: str = "cuda"
    blocks_to_swap: int = Field(default=0, ge=0)
    max_checkpoints: int = Field(default=32, ge=1, le=64)


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
    training_commands = TrainingCommandService(root)
    samples = SampleService(root)
    workbench = WorkbenchCommandService(root)
    metadata = MetadataService(root)
    catalog = LoraCatalogService(root)
    repair = RepairService(root)

    app = FastAPI(
        title="Fizgig Browser API",
        version="0.1.0",
        description="Browser-safe control plane for the Fizgig workbench.",
    )

    api_token = os.environ.get("FIZGIG_API_TOKEN", "").strip()

    @app.middleware("http")
    async def optional_api_auth(request, call_next):
        """Protect API routes when a deployment supplies a bearer token.

        Local development remains unauthenticated when the environment
        variable is absent. Health is intentionally public for deployment
        probes; all other API routes require the configured token.
        """
        if api_token and request.url.path.startswith("/api/") and request.url.path != "/api/health":
            authorization = request.headers.get("authorization", "")
            if authorization != f"Bearer {api_token}":
                return JSONResponse({"detail": "authentication required"}, status_code=401, headers={"WWW-Authenticate": "Bearer"})
        return await call_next(request)

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

    @app.post("/api/training/command-preview")
    def preview_training_command(request: TrainingLaunchRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            launch = training_commands.from_mapping(values)
            return training_commands.preview(launch)
        except TrainingLaunchError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/training/start")
    def start_training(request: TrainingLaunchRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            launch = training_commands.from_mapping(values)
            preview = training_commands.preview(launch)
        except TrainingLaunchError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        payload = {"request": values, "command": preview["command"]}

        def run(context, job_payload):
            return run_training_job(context, job_payload, training_commands)

        return jobs.create("training.run", payload, run).as_dict()

    @app.post("/api/samples/prompts")
    def write_sample_prompts(request: SamplePromptsRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            return samples.write_prompts(**values)
        except (SampleError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/samples/override")
    def write_sample_override(request: SampleOverrideRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            return samples.write_override(**values)
        except (SampleError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/samples/override")
    def clear_sample_override(output_dir: str = Query(min_length=1)) -> dict[str, str]:
        try:
            samples.clear_override(output_dir)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return {"output_dir": output_dir, "status": "cleared"}

    def _tool_job(tool: str, command: list[str]) -> dict[str, Any]:
        payload = {"tool": tool, "command": command}

        def run(context, job_payload):
            return run_workbench_job(context, job_payload["command"], workbench, tool)

        return jobs.create(f"workbench.{tool}", payload, run).as_dict()

    @app.post("/api/workbench/profile/preview")
    def preview_profile(request: ProfileToolRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            command = workbench.profile(ProfileRequest(**values))
            return workbench.preview(command, "profile")
        except (WorkbenchError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workbench/profile/start")
    def start_profile(request: ProfileToolRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            command = workbench.profile(ProfileRequest(**values))
        except (WorkbenchError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _tool_job("profile", command)

    @app.post("/api/workbench/extract/preview")
    def preview_extract(request: ExtractToolRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            command = workbench.extract(ExtractRequest(**values))
            return workbench.preview(command, "extract")
        except (WorkbenchError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/workbench/extract/start")
    def start_extract(request: ExtractToolRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            command = workbench.extract(ExtractRequest(**values))
        except (WorkbenchError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        return _tool_job("extract", command)

    @app.get("/api/repair/default-state")
    def get_repair_default_state(family: str = Query(default="klein", min_length=1)) -> dict[str, Any]:
        try:
            return {"family": family, "state": repair.default_state(family)}
        except (RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/repair/bake/preview")
    def preview_repair_bake(request: RepairBakeRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            paths = repair.validate(**values)
            return {
                "operation": "repair.bake",
                "primary": paths["primary"],
                "donor": paths["donor"],
                "output": paths["output"],
                "execution_ready": True,
            }
        except (RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/repair/bake/start")
    def start_repair_bake(request: RepairBakeRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            repair.validate(**values)
        except (RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def run(context, payload):
            context.update(progress=10, message="Baking repaired LoRA")
            result = repair.bake(**payload)
            context.update(progress=100, message="Repair bake complete")
            return result

        return jobs.create("repair.bake", values, run).as_dict()

    @app.post("/api/repair/render/preview")
    def preview_repair_render(request: RepairRenderRequest) -> dict[str, Any]:
        """Validate a GPU preview request without loading model weights."""
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            repair.validate_state(values["state"])
            repair._input(values["primary"], "primary LoRA")
            if values.get("donor", ""):
                repair._input(values["donor"], "donor LoRA")
            output_path = repair.paths.resolve_child(values["output"])
            if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
                raise RepairError("preview output must be a PNG, JPEG, or WebP file")
            for key in ("dit", "vae", "text_encoder"):
                repair._input(values[key], key.replace("_", " "))
            repair.default_state(values["family"])
            return {"operation": "repair.render", "family": values["family"], "output": values["output"], "execution_ready": True}
        except (RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.post("/api/repair/render/start")
    def start_repair_render(request: RepairRenderRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            repair.default_state(values["family"])
            for key in ("dit", "vae", "text_encoder"):
                repair._input(values[key], key.replace("_", " "))
        except RepairError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def run(context, payload):
            context.update(progress=5, message="Loading Repair Studio model")
            result = repair.render_preview(**payload)
            context.update(progress=100, message="Repair preview complete")
            return result

        return jobs.create("repair.render", values, run).as_dict()

    @app.post("/api/lora/explorer/render/start")
    def start_explorer_render(request: ExplorerRenderRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            repair.validate_state(values["state"])
            for key in ("primary", "dit", "vae", "text_encoder"):
                repair._input(values[key], key.replace("_", " "))
            if values.get("donor", ""):
                repair._input(values["donor"], "donor LoRA")
            repair.paths.resolve_child(values["output_dir"])
            repair.default_state(values["family"])
        except (RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def run(context, payload):
            context.update(progress=5, message="Loading Explorer model")
            result = repair.render_explorer_variants(**payload)
            context.update(progress=100, message="Explorer variants complete")
            return result

        return jobs.create("lora.explorer.render", values, run).as_dict()

    @app.post("/api/lora/royale/render/start")
    def start_royale_render(request: RoyaleRenderRequest) -> dict[str, Any]:
        try:
            values = request.model_dump() if hasattr(request, "model_dump") else request.dict()
            folder = catalog._folder(values["folder"])
            from fizgig.lora_royale.scan import scan_checkpoints
            if not scan_checkpoints(str(folder)):
                raise CatalogError("no SafeTensors checkpoints found")
            for key in ("dit", "vae", "text_encoder"):
                repair._input(values[key], key.replace("_", " "))
            repair.paths.resolve_child(values["output_dir"])
            repair.default_state(values["family"])
        except (CatalogError, RepairError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        def run(context, payload):
            context.update(progress=5, message="Loading Royale model")
            result = repair.render_royale_checkpoints(**payload)
            context.update(progress=100, message="Royale sequence complete")
            return result

        return jobs.create("lora.royale.render", values, run).as_dict()

    @app.get("/api/metadata/inspect")
    def inspect_metadata(path: str = Query(min_length=1)) -> dict[str, Any]:
        try:
            return metadata.inspect(path)
        except MetadataError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/lora/explorer")
    def list_lora_catalog(folder: str = Query(default="output_loras", min_length=1)) -> dict[str, Any]:
        try:
            return {"folder": folder, "items": catalog.explorer(folder)}
        except (CatalogError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/lora/royale")
    def list_royale_checkpoints(folder: str = Query(default="output_loras", min_length=1)) -> dict[str, Any]:
        try:
            return {"folder": folder, "items": catalog.royale(folder)}
        except (CatalogError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

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

    @app.get("/api/jobs/{job_id}/log", response_class=PlainTextResponse)
    def read_job_log(job_id: str, max_chars: int = Query(default=100_000, ge=1, le=1_000_000)) -> str:
        try:
            jobs.get(job_id)
            log_path = root / ".fizgig" / "jobs" / f"{job_id}.log"
            if not log_path.is_file():
                raise HTTPException(status_code=404, detail="job log not found")
            return log_path.read_text(encoding="utf-8", errors="replace")[-max_chars:]
        except KeyError as exc:
            raise HTTPException(status_code=404, detail=str(exc)) from exc
        except OSError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/artifacts/download")
    def download_artifact(path: str = Query(min_length=1)) -> FileResponse:
        """Download a workspace artifact without exposing host paths."""
        try:
            artifact = WorkspacePaths(root).resolve_child(path)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="artifact must stay inside the workspace") from exc
        if not artifact.is_file():
            raise HTTPException(status_code=404, detail="artifact not found")
        return FileResponse(artifact, filename=artifact.name)

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

    @app.get("/logo.jpg", include_in_schema=False)
    def ui_logo() -> FileResponse:
        """Serve the original Fizgig workflow artwork with the browser UI."""
        logo = Path(__file__).resolve().parents[3] / "logo.jpg"
        if not logo.is_file():
            raise HTTPException(status_code=404, detail="Fizgig logo is not installed")
        return FileResponse(logo, media_type="image/jpeg")

    # A production image can build the React bundle into web/dist. Mount it
    # last so all /api routes above retain precedence while the same HTTP
    # origin serves the browser app without Vite or noVNC.
    frontend_dist = Path(os.environ.get("FIZGIG_FRONTEND_DIST", str(root / "web" / "dist"))).expanduser().resolve()
    if not frontend_dist.is_dir():
        source_dist = Path(__file__).resolve().parents[3] / "web" / "dist"
        if source_dist.is_dir():
            frontend_dist = source_dist
    if frontend_dist.is_dir() and (frontend_dist / "index.html").is_file():
        app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="frontend")

    return app


app = create_app()
