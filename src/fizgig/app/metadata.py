"""Header-only SafeTensors inspection for the browser Metadata surface."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from fizgig.app.state import WorkspacePaths


class MetadataError(ValueError):
    """Raised when a SafeTensors file cannot be inspected."""


class MetadataService:
    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(workspace_root)

    def inspect(self, value: str) -> dict[str, Any]:
        path = Path(str(value).strip()).expanduser()
        if not path.is_absolute():
            path = self.paths.resolve_child(path)
        if not path.is_file():
            raise MetadataError(f"file does not exist: {value}")
        if path.suffix.lower() != ".safetensors":
            raise MetadataError("metadata inspection currently supports .safetensors files")
        try:
            with path.open("rb") as handle:
                raw_length = handle.read(8)
                if len(raw_length) != 8:
                    raise MetadataError("file is too small to contain a SafeTensors header")
                header_length = int.from_bytes(raw_length, "little")
                if header_length <= 0 or header_length > 100 * 1024 * 1024:
                    raise MetadataError("SafeTensors header length is invalid")
                header = json.loads(handle.read(header_length).decode("utf-8"))
        except MetadataError:
            raise
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise MetadataError(f"unable to read SafeTensors header: {exc}") from exc
        if not isinstance(header, dict):
            raise MetadataError("SafeTensors header is not an object")
        metadata = header.pop("__metadata__", {})
        if not isinstance(metadata, dict):
            metadata = {}
        tensors = []
        for name, spec in header.items():
            if not isinstance(spec, dict):
                continue
            tensors.append({
                "name": name,
                "dtype": spec.get("dtype"),
                "shape": spec.get("shape"),
                "data_offsets": spec.get("data_offsets"),
            })
        relative: str | None
        try:
            relative = path.relative_to(self.paths.root).as_posix()
        except ValueError:
            relative = None
        return {
            "path": str(path),
            "relative_path": relative,
            "size_bytes": path.stat().st_size,
            "tensor_count": len(tensors),
            "metadata": metadata,
            "tensors": tensors,
        }
