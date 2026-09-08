"""Small, frontend-neutral state and workspace primitives.

This module deliberately has no Tkinter, HTTP, Modal, or model imports.  The
desktop and browser frontends can use the same persistence rules while the
larger GUI is migrated incrementally.
"""

from __future__ import annotations

import copy
import json
import os
from pathlib import Path
from typing import Any, Callable, Mapping


JsonObject = dict[str, Any]


class WorkspacePaths:
    """Resolve user-facing paths beneath one Fizgig workspace.

    Model files may live outside the workspace and are therefore accepted as
    absolute paths.  Browser-managed artifacts should use ``resolve_child`` so
    a request cannot escape the workspace through ``..`` or a symlinked path.
    """

    def __init__(self, root: str | os.PathLike[str]) -> None:
        self.root = Path(root).expanduser().resolve()

    def resolve_child(self, value: str | os.PathLike[str]) -> Path:
        """Return an existing-or-new path guaranteed to be inside ``root``."""

        candidate = Path(value)
        if candidate.is_absolute():
            resolved = candidate.resolve()
        else:
            resolved = (self.root / candidate).resolve()
        try:
            resolved.relative_to(self.root)
        except ValueError as exc:
            raise ValueError("path is outside the workspace") from exc
        return resolved

    def relative_or_absolute(self, value: str | os.PathLike[str]) -> str:
        """Serialize a path relative to the workspace when possible."""

        path = Path(value).expanduser().resolve()
        try:
            relative = path.relative_to(self.root)
        except ValueError:
            return os.path.normpath(str(path)).replace(os.sep, "/")
        return relative.as_posix() or "."

    def resolve_stored_path(self, value: str | os.PathLike[str]) -> str:
        """Resolve a stored relative path, preserving external absolute paths."""

        if not value:
            return ""
        path = Path(value).expanduser()
        if path.is_absolute():
            return os.path.normpath(str(path))
        return str(self.resolve_child(path))


class JsonStateStore:
    """Atomic JSON state store with tolerant reads and injectable migrations."""

    def __init__(self, path: str | os.PathLike[str]) -> None:
        self.path = Path(path).expanduser()

    def load(
        self,
        defaults: Mapping[str, Any] | None = None,
        migrate: Callable[[JsonObject], JsonObject] | None = None,
    ) -> JsonObject:
        state: JsonObject = copy.deepcopy(dict(defaults or {}))
        try:
            with self.path.open("r", encoding="utf-8") as handle:
                saved = json.load(handle)
            if isinstance(saved, dict):
                state.update(saved)
        except (OSError, json.JSONDecodeError, TypeError):
            # A missing or interrupted state file should not prevent startup.
            pass
        if migrate is not None:
            state = migrate(state)
        return state

    def save(self, state: Mapping[str, Any]) -> None:
        """Write JSON atomically and create its parent directory if needed."""

        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_name(self.path.name + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(dict(state), handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.path)

