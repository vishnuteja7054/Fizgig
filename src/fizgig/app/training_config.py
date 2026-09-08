"""Compatible dataset TOML generation for the browser training surface."""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
from dataclasses import dataclass
from pathlib import Path

from fizgig.app.state import WorkspacePaths


class TrainingConfigError(ValueError):
    """Raised when a browser training configuration is invalid."""


@dataclass(frozen=True)
class DatasetConfigRequest:
    name: str = "Fizgig_train"
    folder: str = "dataset"
    target_megapixels: float = 0.25
    batch_size: int = 1
    caption_extension: str = ".txt"
    enable_bucket: bool = True
    bucket_no_upscale: bool = True
    cache_root: str = "cache"


class TrainingConfigService:
    """Write the image dataset TOML shared by Fizgig's training scripts."""

    _INVALID_NAME = re.compile(r'[<>:"/\\|?*]')
    BUCKET_STEP = 16

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(workspace_root)
        self.dataset_root = self.paths.resolve_child("dataset")

    def _validate_request(self, request: DatasetConfigRequest) -> tuple[int, Path, Path]:
        name = str(request.name).strip()
        if not name or name in {".", ".."} or self._INVALID_NAME.search(name):
            raise TrainingConfigError("dataset config name contains invalid characters")
        try:
            megapixels = float(request.target_megapixels)
        except (TypeError, ValueError) as exc:
            raise TrainingConfigError("target megapixels must be a number") from exc
        if not math.isfinite(megapixels) or megapixels <= 0 or megapixels > 100:
            raise TrainingConfigError("target megapixels must be greater than 0 and at most 100")
        if int(request.batch_size) < 1 or int(request.batch_size) > 1024:
            raise TrainingConfigError("batch size must be between 1 and 1024")
        caption_extension = str(request.caption_extension).strip()
        if not caption_extension.startswith(".") or "/" in caption_extension or "\\" in caption_extension:
            raise TrainingConfigError("caption extension must look like .txt")
        folder = self.paths.resolve_child(request.folder)
        if not folder.is_dir():
            raise TrainingConfigError(f"dataset folder does not exist: {request.folder}")
        cache_root = self.paths.resolve_child(request.cache_root)
        return (
            max(self.BUCKET_STEP, int(math.sqrt(megapixels * 1_000_000)) // self.BUCKET_STEP * self.BUCKET_STEP),
            folder,
            cache_root,
        )

    @staticmethod
    def _cache_dir_for(cache_root: Path, folder: Path) -> Path:
        normalized = folder.as_posix().lower().rstrip("/")
        digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:8]
        basename = re.sub(r"[^A-Za-z0-9_-]+", "_", folder.name) or "dataset"
        return cache_root / f"{basename}-{digest}"

    def build(self, request: DatasetConfigRequest) -> tuple[Path, str]:
        side, folder, cache_root = self._validate_request(request)
        cache_directory = self._cache_dir_for(cache_root, folder)
        self.dataset_root.mkdir(parents=True, exist_ok=True)
        output = self.dataset_root / f"{request.name.strip()}.toml"
        quote = json.dumps
        content = "\n".join([
            "[general]",
            f"resolution = [{side}, {side}]",
            f"caption_extension = {quote(request.caption_extension.strip())}",
            f"batch_size = {int(request.batch_size)}",
            "num_repeats = 1",
            f"enable_bucket = {str(bool(request.enable_bucket)).lower()}",
            f"bucket_no_upscale = {str(bool(request.bucket_no_upscale)).lower()}",
            "",
            "[[datasets]]",
            f"image_directory = {quote(folder.as_posix())}",
            f"cache_directory = {quote(cache_directory.as_posix())}",
            "",
        ])
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(content, encoding="utf-8")
        os.replace(temporary, output)
        return output, content
