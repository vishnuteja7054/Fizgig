"""Workspace-safe LoRA catalogs for Explorer and Royale."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from fizgig.app.metadata import MetadataService
from fizgig.app.state import WorkspacePaths
from fizgig.lora_royale.scan import scan_checkpoints


class CatalogError(ValueError):
    pass


class LoraCatalogService:
    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(workspace_root)
        self.metadata = MetadataService(workspace_root)

    def _folder(self, value: str) -> Path:
        try:
            folder = self.paths.resolve_child(value)
        except ValueError as exc:
            raise CatalogError("folder must stay inside the workspace") from exc
        if not folder.is_dir():
            raise CatalogError(f"folder does not exist: {value}")
        return folder

    def explorer(self, folder: str = "output_loras") -> list[dict[str, Any]]:
        root = self._folder(folder)
        items = []
        for path in sorted(root.glob("*.safetensors"), key=lambda item: item.name.casefold()):
            info: dict[str, Any] = {
                "name": path.stem,
                "relative_path": path.relative_to(self.paths.root).as_posix(),
                "size_bytes": path.stat().st_size,
            }
            try:
                inspected = self.metadata.inspect(str(path))
                info["metadata"] = inspected["metadata"]
                info["tensor_count"] = inspected["tensor_count"]
            except Exception as exc:
                info["metadata"] = {}
                info["error"] = str(exc)
            items.append(info)
        return items

    def royale(self, folder: str = "output_loras") -> list[dict[str, Any]]:
        root = self._folder(folder)
        checkpoints = scan_checkpoints(str(root))
        return [{
            "label": str(label),
            "relative_path": Path(path).relative_to(self.paths.root).as_posix(),
            "size_bytes": Path(path).stat().st_size,
        } for label, path in checkpoints]
