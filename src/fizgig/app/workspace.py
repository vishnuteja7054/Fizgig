"""Browser-safe workspace state shared with Fizgig's desktop last-used file."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from fizgig.app.state import JsonObject, JsonStateStore, WorkspacePaths


DEFAULT_WORKSPACE_STATE: dict[str, Any] = {
    "dataset_folder": "dataset",
    "architecture": "Klein 9B",
    "caption_trigger": "trigger_word",
    "prep_mode": "Resize Only",
    "prep_megapixels": "1.0",
    "prep_replace_originals": False,
}


class WorkspaceStateError(ValueError):
    """Raised when a browser state update cannot be represented safely."""


class WorkspaceStateService:
    """Persist a narrow browser state patch without discarding desktop keys."""

    STATE_FILENAME = ".last_used.json"
    _ALLOWED_TYPES = (bool, int, float, str, type(None))

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        paths = WorkspacePaths(workspace_root)
        self.store = JsonStateStore(paths.resolve_child(self.STATE_FILENAME))

    def load(self) -> JsonObject:
        return self.store.load(DEFAULT_WORKSPACE_STATE)

    def update(self, values: Mapping[str, Any]) -> JsonObject:
        if not isinstance(values, Mapping):
            raise WorkspaceStateError("workspace state must be a JSON object")
        patch: dict[str, Any] = {}
        for key, value in values.items():
            if not isinstance(key, str) or not key.strip():
                raise WorkspaceStateError("workspace state keys must be non-empty strings")
            if not isinstance(value, self._ALLOWED_TYPES):
                raise WorkspaceStateError(f"workspace state value is not JSON-safe: {key}")
            patch[key] = value
        state = self.load()
        state.update(patch)
        self.store.save(state)
        return state
