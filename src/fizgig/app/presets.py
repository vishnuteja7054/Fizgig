"""Frontend-neutral custom preset repository.

The desktop GUI currently owns preset dialogs and filesystem access.  This
repository keeps the file format compatible while giving the browser API a
small, explicit contract with no UI dependencies.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Mapping

from fizgig.app.state import JsonStateStore, WorkspacePaths


class PresetError(ValueError):
    """Base class for user-correctable preset errors."""


class PresetExistsError(PresetError):
    pass


class PresetNotFoundError(PresetError):
    pass


class PresetRepository:
    """Read and write custom presets in ``<root>/presets/<architecture>``."""

    _INVALID_NAME_CHARS = frozenset('<>:"/\\|?*')

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(root)
        self.presets_root = self.paths.resolve_child("presets")

    @classmethod
    def _validate_component(cls, value: str, label: str) -> str:
        value = str(value).strip()
        if not value or value in {".", ".."}:
            raise PresetError(f"{label} cannot be empty")
        if any(char in cls._INVALID_NAME_CHARS for char in value):
            raise PresetError(f"{label} contains an invalid filename character")
        return value

    def _directory(self, architecture: str) -> Path:
        architecture = self._validate_component(architecture, "architecture")
        return self.paths.resolve_child(Path("presets") / architecture)

    def _file(self, architecture: str, name: str) -> Path:
        name = self._validate_component(name, "preset name")
        return self._directory(architecture) / f"{name}.json"

    def list(self, architecture: str) -> list[str]:
        directory = self._directory(architecture)
        if not directory.is_dir():
            return []
        return sorted(
            entry.stem
            for entry in directory.iterdir()
            if entry.is_file() and entry.suffix.lower() == ".json"
        )

    def load(self, architecture: str, name: str) -> dict[str, Any]:
        path = self._file(architecture, name)
        if not path.is_file():
            raise PresetNotFoundError(f"preset not found: {name}")
        try:
            value = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PresetError(f"could not read preset: {name}") from exc
        if not isinstance(value, dict):
            raise PresetError(f"preset must contain a JSON object: {name}")
        return value

    def save(
        self,
        architecture: str,
        name: str,
        values: Mapping[str, Any],
        *,
        overwrite: bool = False,
    ) -> Path:
        if not isinstance(values, Mapping):
            raise PresetError("preset values must be a JSON object")
        path = self._file(architecture, name)
        if path.exists() and not overwrite:
            raise PresetExistsError(f"preset already exists: {name}")
        JsonStateStore(path).save(values)
        return path

    def delete(self, architecture: str, name: str) -> None:
        path = self._file(architecture, name)
        if not path.is_file():
            raise PresetNotFoundError(f"preset not found: {name}")
        path.unlink()

