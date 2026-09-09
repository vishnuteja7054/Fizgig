"""Command builders for browser workbench tools."""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fizgig.app.jobs import JobCancelled, JobContext
from fizgig.app.state import WorkspacePaths


class WorkbenchError(ValueError):
    """Raised when a workbench request is invalid."""


@dataclass(frozen=True)
class ProfileRequest:
    lora: str
    output: str = "out/profile.html"
    krea2: bool = True
    dit: str = ""
    vae: str = ""
    text_encoder: str = ""
    num_samples: int = 8
    num_bins: int = 5
    width: int = 1024
    height: int = 1024
    prompt: str = ""
    blocks_to_swap: int = 12
    seed: int | None = None


@dataclass(frozen=True)
class ExtractRequest:
    source: str
    output: str = "output_loras/extracted.safetensors"
    samples: int = 0
    rank: int = 2
    blocks: str = "all"
    custom_blocks: str = ""
    timesteps: str = "all"
    prompt: str = "a photo"
    width: int = 1024
    height: int = 1024
    multiplier: float = 1.0
    seed: int | None = None
    dit: str = ""
    vae: str = ""
    text_encoder: str = ""


class WorkbenchCommandService:
    """Build safe argv for existing Fizgig workbench scripts."""

    def __init__(self, workspace_root: str | os.PathLike[str], *, project_root: str | os.PathLike[str] | None = None, python_executable: str | None = None) -> None:
        self.paths = WorkspacePaths(workspace_root)
        self.project_root = Path(project_root or Path(__file__).resolve().parents[3]).expanduser().resolve()
        self.python_executable = python_executable or sys.executable

    def _input(self, value: str, label: str) -> str:
        path = Path(str(value).strip()).expanduser()
        if not path.is_absolute():
            path = self.paths.resolve_child(path)
        if not path.is_file():
            raise WorkbenchError(f"{label} does not exist: {value}")
        return str(path)

    def _output(self, value: str, label: str) -> str:
        if not str(value).strip():
            raise WorkbenchError(f"{label} is required")
        try:
            path = self.paths.resolve_child(value)
        except ValueError as exc:
            raise WorkbenchError(f"{label} must stay inside the workspace") from exc
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    def profile(self, request: ProfileRequest) -> list[str]:
        lora = self._input(request.lora, "lora")
        output = self._output(request.output, "profile output")
        if int(request.num_samples) < 1 or int(request.num_bins) < 1:
            raise WorkbenchError("profile samples and bins must be positive")
        if request.krea2:
            return [self.python_executable, str(self.project_root / "src/fizgig/scripts/profile_lora.py"),
                    "--lora", lora, "--krea2", "--output", output]
        dit = self._input(request.dit, "dit")
        vae = self._input(request.vae, "vae")
        text_encoder = self._input(request.text_encoder, "text_encoder")
        command = [self.python_executable, str(self.project_root / "src/fizgig/scripts/profile_lora.py"),
                   "--lora", lora, "--dit", dit, "--vae", vae, "--text_encoder", text_encoder,
                   "--output", output, "--num_samples", str(request.num_samples),
                   "--num_bins", str(request.num_bins), "--width", str(request.width),
                   "--height", str(request.height), "--blocks_to_swap", str(request.blocks_to_swap)]
        if request.prompt.strip():
            command += ["--prompt", request.prompt.strip()]
        if request.seed is not None:
            command += ["--seed", str(request.seed)]
        return command

    def extract(self, request: ExtractRequest) -> list[str]:
        source = self._input(request.source, "source LoRA")
        output = self._output(request.output, "extraction output")
        if int(request.samples) < 0 or int(request.rank) < 1:
            raise WorkbenchError("samples must be non-negative and rank must be positive")
        if request.timesteps not in {"all", "early", "mid", "late", "midlate", "earlymid"}:
            raise WorkbenchError("invalid timestep preset")
        command = [self.python_executable, str(self.project_root / "src/fizgig/scripts/extract_lora.py"),
                   "--source", source, "--output", output, "--rank", str(request.rank),
                   "--blocks", request.blocks, "--timesteps", request.timesteps,
                   "--samples", str(request.samples), "--prompt", request.prompt,
                   "--width", str(request.width), "--height", str(request.height),
                   "--multiplier", str(request.multiplier)]
        if request.custom_blocks.strip():
            command += ["--custom_blocks", request.custom_blocks.strip()]
        if request.seed is not None:
            command += ["--seed", str(request.seed)]
        if int(request.samples) > 0:
            command += ["--dit", self._input(request.dit, "dit"), "--vae", self._input(request.vae, "vae"),
                        "--text_encoder", self._input(request.text_encoder, "text_encoder")]
        return command

    def preview(self, command: list[str], name: str) -> dict[str, Any]:
        return {"tool": name, "command": command, "shell_command": shlex.join(command),
                "working_directory": str(self.project_root), "execution_ready": True}


def run_workbench_job(context: JobContext, command: list[str], service: WorkbenchCommandService, tool: str) -> dict[str, Any]:
    log_path = service.paths.resolve_child(f".fizgig/jobs/{context.job_id}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    process = subprocess.Popen(command, cwd=str(service.project_root), env={**os.environ, "PYTHONUNBUFFERED": "1"},
                               stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
    try:
        with log_path.open("w", encoding="utf-8") as log:
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                context.update(message=f"{tool}: {line.rstrip()[-240:]}")
                if context.service.get(context.job_id).cancel_requested:
                    process.terminate()
                    raise JobCancelled()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"{tool} exited with code {return_code}")
    except JobCancelled:
        if process.poll() is None:
            process.terminate()
        try:
            process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()
        raise
    finally:
        if process.poll() is None:
            process.kill()
            process.wait()
    return {"tool": tool, "return_code": 0, "log_relative_path": log_path.relative_to(service.paths.root).as_posix()}
