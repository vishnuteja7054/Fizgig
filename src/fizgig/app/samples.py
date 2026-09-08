"""Workspace-safe sample prompt and live-override files."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from fizgig.app.state import WorkspacePaths


class SampleError(ValueError):
    """Raised when sample settings cannot be written safely."""


class SampleService:
    """Write the prompt/override artifacts consumed by Fizgig trainers."""

    _SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")

    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(workspace_root)

    def write_prompts(self, name: str, text: str, *, folder: str = "samples") -> dict[str, Any]:
        name = str(name).strip()
        if not self._SAFE_NAME.fullmatch(name) or not name.lower().endswith(".txt"):
            raise SampleError("prompt filename must be a simple .txt filename")
        prompts = [line.strip() for line in str(text).splitlines()
                   if line.strip() and not line.lstrip().startswith("#")]
        if not prompts:
            raise SampleError("enter at least one non-empty sample prompt")
        directory = self.paths.resolve_child(folder)
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / name
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text("\n".join(prompts) + "\n", encoding="utf-8")
        os.replace(temporary, output)
        return {
            "relative_path": output.relative_to(self.paths.root).as_posix(),
            "prompts": prompts,
            "count": len(prompts),
        }

    def write_override(
        self,
        output_dir: str,
        *,
        prompt: str = "",
        seed: int = 1234,
        width: int = 768,
        height: int = 768,
        ref_image: str = "",
    ) -> dict[str, Any]:
        prompt = str(prompt).strip()
        ref_image = str(ref_image).strip()
        if not prompt and not ref_image:
            raise SampleError("a live sample override needs a prompt or reference image")
        if int(width) < 16 or int(height) < 16 or int(width) > 8192 or int(height) > 8192:
            raise SampleError("sample dimensions must be between 16 and 8192")
        directory = self.paths.resolve_child(output_dir)
        directory.mkdir(parents=True, exist_ok=True)
        output = directory / ".sample_override.json"
        data = {"prompt": prompt, "seed": int(seed), "width": int(width),
                "height": int(height), "ref_image": ref_image}
        temporary = output.with_name(output.name + ".tmp")
        temporary.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        os.replace(temporary, output)
        return {"relative_path": output.relative_to(self.paths.root).as_posix(), **data}

    def clear_override(self, output_dir: str) -> None:
        output = self.paths.resolve_child(output_dir) / ".sample_override.json"
        try:
            output.unlink()
        except FileNotFoundError:
            pass
