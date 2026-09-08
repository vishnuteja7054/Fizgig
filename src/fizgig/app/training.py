"""Browser-safe training command generation and subprocess execution.

The desktop GUI contains a large amount of Tk state around these commands.
This module keeps the actual CLI contracts in a small, testable service so a
browser client can preview exactly what will run before it starts a model job.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Mapping, Sequence

from fizgig.app.jobs import JobCancelled, JobContext
from fizgig.app.state import WorkspacePaths


class TrainingLaunchError(ValueError):
    """Raised when a training launch request cannot be made safely."""


ARCHITECTURES = (
    "Flux 2 Klein Base 9B",
    "Krea 2",
    "MiniMax H3",
)


@dataclass(frozen=True)
class TrainingLaunchRequest:
    architecture: str
    dataset_config: str
    dit: str
    output_dir: str = "output_loras"
    output_name: str = "fizgig_lora"
    vae: str = ""
    text_encoder: str = ""
    network_dim: int = 16
    network_alpha: float = 16
    learning_rate: float = 1e-4
    max_train_epochs: int = 10
    save_every_n_epochs: int = 0
    seed: int = 42
    blocks_to_swap: int | str = 0
    optimizer_type: str = "adamw8bit"
    optimizer_args: str = ""
    gradient_checkpointing: bool = True
    gradient_accumulation_steps: int = 1
    max_grad_norm: float = 1.0
    network_type: str = "lora"
    lokr_factor: int = 8
    lora_lr_ratio: int = 1
    save_state: bool = True
    save_state_on_train_end: bool = True
    keep_last_n_states: int = 2
    resume: str = ""
    quantize_4bit: bool = False
    quant_int8: str = ""
    base_quant: str = "auto"
    use_fp8_base: bool = True
    discrete_flow_shift: float = 2.5
    sample_prompts: str = ""
    sample_every_n_epochs: int = 0
    sample_at_first: bool = False
    sample_width: int = 512
    sample_height: int = 512
    sample_steps: int = 8
    sample_cfg_scale: float = 1.0
    sample_negative: str = ""
    sample_seed: int = 42
    extra_args: tuple[str, ...] = field(default_factory=tuple)


def _as_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return bool(value)


class TrainingCommandService:
    """Build commands without importing torch or requiring a GPU."""

    def __init__(
        self,
        workspace_root: str | os.PathLike[str],
        *,
        project_root: str | os.PathLike[str] | None = None,
        python_executable: str | None = None,
        accelerate_executable: str = "accelerate",
    ) -> None:
        self.paths = WorkspacePaths(workspace_root)
        self.project_root = Path(project_root or Path(__file__).resolve().parents[3]).expanduser().resolve()
        self.python_executable = python_executable or sys.executable
        self.accelerate_executable = accelerate_executable

    @staticmethod
    def from_mapping(values: Mapping[str, Any]) -> TrainingLaunchRequest:
        allowed = {field_name for field_name in TrainingLaunchRequest.__dataclass_fields__}
        unknown = sorted(set(values) - allowed)
        if unknown:
            raise TrainingLaunchError(f"unknown training field(s): {', '.join(unknown)}")
        data = dict(values)
        if "extra_args" in data:
            data["extra_args"] = tuple(str(item) for item in data["extra_args"])
        try:
            return TrainingLaunchRequest(**data)
        except TypeError as exc:
            raise TrainingLaunchError(str(exc)) from exc

    @staticmethod
    def _architecture(value: str) -> str:
        normalized = str(value).strip().casefold()
        for architecture in ARCHITECTURES:
            if normalized == architecture.casefold():
                return architecture
        raise TrainingLaunchError(
            f"unsupported architecture {value!r}; choose one of: {', '.join(ARCHITECTURES)}"
        )

    def _workspace_file(self, value: str, label: str, *, must_exist: bool) -> str:
        value = str(value or "").strip()
        if not value:
            raise TrainingLaunchError(f"{label} is required")
        path = Path(value).expanduser()
        try:
            resolved = path if path.is_absolute() else self.paths.resolve_child(path)
        except ValueError as exc:
            raise TrainingLaunchError(f"{label} path is invalid: {exc}") from exc
        if must_exist and not resolved.is_file():
            raise TrainingLaunchError(f"{label} does not exist: {value}")
        return str(resolved)

    def _model_file(self, value: str, label: str, *, required: bool, must_exist: bool = False) -> str:
        value = str(value or "").strip()
        if not value:
            if required:
                raise TrainingLaunchError(f"{label} is required")
            return ""
        path = Path(value).expanduser()
        try:
            resolved = path if path.is_absolute() else self.paths.resolve_child(path)
        except ValueError as exc:
            raise TrainingLaunchError(f"{label} path is invalid: {exc}") from exc
        if must_exist and not resolved.is_file():
            raise TrainingLaunchError(f"{label} does not exist: {value}")
        return str(resolved)

    def _validate(self, request: TrainingLaunchRequest) -> tuple[str, dict[str, str]]:
        architecture = self._architecture(request.architecture)
        try:
            dataset_config = self._workspace_file(request.dataset_config, "dataset_config", must_exist=True)
        except ValueError as exc:
            raise TrainingLaunchError(str(exc)) from exc
        try:
            dit = self._model_file(request.dit, "dit", required=True, must_exist=True)
        except ValueError as exc:
            raise TrainingLaunchError(f"dit is invalid: {exc}") from exc
        try:
            output_dir = self.paths.resolve_child(request.output_dir)
        except ValueError as exc:
            raise TrainingLaunchError(f"output_dir is invalid: {exc}") from exc
        output_dir.mkdir(parents=True, exist_ok=True)
        output_name = str(request.output_name).strip()
        if not output_name or output_name in {".", ".."} or any(char in output_name for char in '/\\'):
            raise TrainingLaunchError("output_name must be a simple filename stem")
        if int(request.network_dim) < 1 or float(request.network_alpha) <= 0:
            raise TrainingLaunchError("network_dim must be positive and network_alpha must be greater than 0")
        if float(request.learning_rate) <= 0 or int(request.max_train_epochs) < 1:
            raise TrainingLaunchError("learning_rate must be positive and max_train_epochs must be at least 1")
        if int(request.save_every_n_epochs) < 0 or int(request.gradient_accumulation_steps) < 1:
            raise TrainingLaunchError("checkpoint frequency and gradient accumulation must be non-negative/positive")
        if int(request.keep_last_n_states) < 1:
            raise TrainingLaunchError("keep_last_n_states must be at least 1")
        if request.network_type not in {"lora", "lokr"}:
            raise TrainingLaunchError("network_type must be lora or lokr")
        try:
            vae = self._model_file(
                request.vae,
                "vae",
                required=architecture == ARCHITECTURES[0],
                must_exist=bool(str(request.vae).strip()),
            )
            text_encoder = self._model_file(
                request.text_encoder,
                "text_encoder",
                required=architecture == ARCHITECTURES[0],
                must_exist=bool(str(request.text_encoder).strip()),
            )
        except ValueError as exc:
            raise TrainingLaunchError(f"model path is invalid: {exc}") from exc
        if int(request.lora_lr_ratio) < 1:
            raise TrainingLaunchError("lora_lr_ratio must be at least 1")
        if architecture == "MiniMax H3":
            if isinstance(request.blocks_to_swap, str) and request.blocks_to_swap != "auto":
                raise TrainingLaunchError("MiniMax blocks_to_swap must be an integer or auto")
            if request.base_quant not in {"auto", "int8", "nf4", "hqq"}:
                raise TrainingLaunchError("MiniMax base_quant is invalid")
        elif not isinstance(request.blocks_to_swap, int) or request.blocks_to_swap < 0:
            raise TrainingLaunchError("blocks_to_swap must be a non-negative integer for this architecture")
        if request.quant_int8 not in {"", "bf16", "int8"}:
            raise TrainingLaunchError("quant_int8 must be empty, bf16, or int8")
        return architecture, {
            "dataset_config": dataset_config,
            "dit": dit,
            "output_dir": str(output_dir),
            "output_name": output_name,
            "vae": vae,
            "text_encoder": text_encoder,
        }

    @staticmethod
    def _add(command: list[str], flag: str, value: Any) -> None:
        command.extend([flag, str(value)])

    def build(self, request: TrainingLaunchRequest) -> list[str]:
        architecture, paths = self._validate(request)
        if architecture == "Flux 2 Klein Base 9B":
            command = [
                self.accelerate_executable, "launch", "--num_cpu_threads_per_process", "2",
                "--mixed_precision", "bf16", str(self.project_root / "src/fizgig/scripts/train.py"),
                "--model_version", "klein-base-9b",
                "--mixed_precision", "bf16",
            ]
            for flag in ("dit", "dataset_config", "vae", "text_encoder"):
                if paths[flag]:
                    self._add(command, f"--{flag}", paths[flag])
            self._add(command, "--blocks_to_swap", request.blocks_to_swap)
            self._add(command, "--optimizer_type", request.optimizer_type)
            self._add(command, "--learning_rate", request.learning_rate)
            self._add(command, "--network_module", "fizgig.networks.lora_klein")
            self._add(command, "--network_dim", request.network_dim)
            self._add(command, "--network_alpha", request.network_alpha)
            command += ["--network_args", f"loraplus_lr_ratio={request.lora_lr_ratio}"]
            self._add(command, "--max_train_epochs", request.max_train_epochs)
            self._add(command, "--save_every_n_epochs", request.save_every_n_epochs)
            self._add(command, "--seed", request.seed)
            self._add(command, "--output_dir", paths["output_dir"])
            self._add(command, "--output_name", paths["output_name"])
            command += ["--timestep_sampling", "sigma", "--discrete_flow_shift", str(request.discrete_flow_shift)]
            if request.gradient_checkpointing:
                command.append("--gradient_checkpointing")
            if request.quantize_4bit:
                command.append("--quant_4bit")
            elif request.use_fp8_base:
                command += ["--fp8_base", "--fp8_scaled"]
            if request.network_type == "lokr":
                raise TrainingLaunchError("Klein currently exposes LoRA, not LoKR, in the browser launcher")
            if request.optimizer_args.strip():
                command += ["--optimizer_args", *request.optimizer_args.split()]
        else:
            script = "krea2_train.py" if architecture == "Krea 2" else "minimax_train.py"
            command = [self.python_executable, str(self.project_root / "src/fizgig/scripts" / script)]
            for flag in ("dit", "dataset_config", "output_dir", "output_name"):
                self._add(command, f"--{flag}", paths[flag])
            for flag, value in (("network_dim", request.network_dim), ("network_alpha", request.network_alpha),
                                ("learning_rate", request.learning_rate),
                                ("max_train_epochs", request.max_train_epochs),
                                ("save_every_n_epochs", request.save_every_n_epochs),
                                ("seed", request.seed), ("network_type", request.network_type),
                                ("lokr_factor", request.lokr_factor),
                                ("gradient_accumulation_steps", request.gradient_accumulation_steps),
                                ("max_grad_norm", request.max_grad_norm),
                                ("optimizer_type", request.optimizer_type)):
                self._add(command, f"--{flag}", value)
            if architecture == "Krea 2":
                self._add(command, "--blocks_to_swap", request.blocks_to_swap)
                self._add(command, "--discrete_flow_shift", request.discrete_flow_shift)
                if not request.use_fp8_base:
                    command.append("--no_fp8")
                if request.quantize_4bit:
                    command.append("--quantize_4bit")
                if request.quant_int8:
                    self._add(command, "--quant_int8", request.quant_int8)
            else:
                self._add(command, "--blocks_to_swap", request.blocks_to_swap or "auto")
                self._add(command, "--base_quant", request.base_quant)
                self._add(command, "--gradient_checkpointing", "auto" if request.gradient_checkpointing else "off")
            if paths["vae"] and architecture in {"Krea 2", "MiniMax H3"}:
                self._add(command, "--vae", paths["vae"])
            if paths["text_encoder"]:
                self._add(command, "--text_encoder", paths["text_encoder"])
            if request.optimizer_args.strip():
                self._add(command, "--optimizer_args", request.optimizer_args.strip())
        if request.save_state:
            command.append("--save_state")
        if request.save_state_on_train_end:
            command.append("--save_state_on_train_end")
        if request.save_state or request.save_state_on_train_end:
            self._add(command, "--keep_last_n_states", request.keep_last_n_states)
        if request.resume.strip():
            self._add(command, "--resume", self._model_file(request.resume, "resume", required=True, must_exist=True))
        if request.sample_prompts.strip():
            prompt_file = self._workspace_file(request.sample_prompts, "sample_prompts", must_exist=True)
            self._add(command, "--sample_prompts", prompt_file)
            self._add(command, "--sample_every_n_epochs", request.sample_every_n_epochs)
            self._add(command, "--sample_width", request.sample_width)
            self._add(command, "--sample_height", request.sample_height)
            self._add(command, "--sample_steps", request.sample_steps)
            self._add(command, "--sample_cfg_scale", request.sample_cfg_scale)
            self._add(command, "--sample_seed", request.sample_seed)
            if request.sample_negative.strip():
                self._add(command, "--sample_negative", request.sample_negative)
            if request.sample_at_first:
                command.append("--sample_at_first")
        command.extend(request.extra_args)
        return command

    def preview(self, request: TrainingLaunchRequest) -> dict[str, Any]:
        command = self.build(request)
        return {
            "architecture": self._architecture(request.architecture),
            "command": command,
            "shell_command": shlex.join(command),
            "working_directory": str(self.project_root),
            "execution_ready": True,
        }


def run_training_job(context: JobContext, payload: dict[str, Any], service: TrainingCommandService) -> dict[str, Any]:
    """Run one validated command, streaming output into its persistent job log."""

    request = service.from_mapping(payload["request"])
    command = service.build(request)
    log_path = service.paths.resolve_child(f".fizgig/jobs/{context.job_id}.log")
    log_path.parent.mkdir(parents=True, exist_ok=True)
    environment = os.environ.copy()
    environment.setdefault("PYTHONUNBUFFERED", "1")
    process = subprocess.Popen(
        command,
        cwd=str(service.project_root),
        env=environment,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )
    try:
        with log_path.open("w", encoding="utf-8") as log:
            assert process.stdout is not None
            for line in process.stdout:
                log.write(line)
                log.flush()
                context.update(message=line.rstrip()[-240:])
                if context.service.get(context.job_id).cancel_requested:
                    process.terminate()
                    raise JobCancelled()
        return_code = process.wait()
        if return_code != 0:
            raise RuntimeError(f"training process exited with code {return_code}")
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
    return {
        "return_code": 0,
        "log_relative_path": log_path.relative_to(service.paths.root).as_posix(),
        "command": command,
    }
