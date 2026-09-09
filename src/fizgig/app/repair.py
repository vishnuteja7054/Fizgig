"""Browser adapter for Repair Studio state and bake operations."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping

from fizgig.app.state import WorkspacePaths


class RepairError(ValueError):
    pass


class RepairService:
    def __init__(self, workspace_root: str | os.PathLike[str]) -> None:
        self.paths = WorkspacePaths(workspace_root)

    @staticmethod
    def default_state(family: str = "klein") -> dict[str, Any]:
        from fizgig.repair_studio.state import SliderState
        normalized = str(family).strip().lower()
        if normalized in {"klein", "klein9b", "flux"}:
            return SliderState.default_klein9b().to_json()
        if normalized in {"krea2", "krea"}:
            return SliderState.default_krea2().to_json()
        if normalized in {"h3", "minimax", "minimaxh3"}:
            return SliderState.default_h3().to_json()
        raise RepairError("family must be klein, krea2, or h3")

    def _input(self, value: str, label: str) -> str:
        path = Path(str(value).strip()).expanduser()
        if not path.is_absolute():
            path = self.paths.resolve_child(path)
        if not path.is_file():
            raise RepairError(f"{label} does not exist: {value}")
        return str(path)

    def _output(self, value: str) -> str:
        try:
            path = self.paths.resolve_child(value)
        except ValueError as exc:
            raise RepairError("output must stay inside the workspace") from exc
        if path.suffix.lower() != ".safetensors":
            raise RepairError("output must be a .safetensors file")
        path.parent.mkdir(parents=True, exist_ok=True)
        return str(path)

    @staticmethod
    def validate_state(state: Mapping[str, Any]) -> None:
        if not isinstance(state, Mapping):
            raise RepairError("state must be a JSON object")
        try:
            from fizgig.repair_studio.state import SliderState
            SliderState.from_json(dict(state))
        except Exception as exc:
            raise RepairError(f"invalid slider state: {exc}") from exc

    def validate(self, primary: str, output: str, state: Mapping[str, Any], donor: str = "") -> dict[str, str]:
        self.validate_state(state)
        return {
            "primary": self._input(primary, "primary LoRA"),
            "donor": self._input(donor, "donor LoRA") if str(donor).strip() else "",
            "output": self._output(output),
        }

    def bake(self, primary: str, output: str, state: Mapping[str, Any], donor: str = "") -> dict[str, Any]:
        paths = self.validate(primary, output, state, donor)
        from fizgig.repair_studio.bake import save_repaired_lora
        from fizgig.repair_studio.state import SliderState
        summary = save_repaired_lora(paths["primary"], SliderState.from_json(dict(state)), paths["output"], paths["donor"] or None)
        return {"output_relative_path": Path(paths["output"]).relative_to(self.paths.root).as_posix(), "summary": summary}

    def render_preview(
        self,
        family: str,
        primary: str,
        output: str,
        state: Mapping[str, Any],
        dit: str,
        vae: str,
        text_encoder: str,
        donor: str = "",
        device: str = "cuda",
        blocks_to_swap: int = 0,
    ) -> dict[str, Any]:
        """Render one GPU preview and save it as a workspace artifact.

        Imports are deliberately inside this method: the browser API can serve
        dataset, metadata, and state requests on a CPU-only process, while a
        render job loads the selected model engine only on the worker device.
        """
        self.validate_state(state)
        paths = {
            "primary": self._input(primary, "primary LoRA"),
            "donor": self._input(donor, "donor LoRA") if str(donor).strip() else "",
        }
        output_path = self.paths.resolve_child(output)
        if output_path.suffix.lower() not in {".png", ".jpg", ".jpeg", ".webp"}:
            raise RepairError("preview output must be a PNG, JPEG, or WebP file")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        model_paths = {
            "dit": self._input(dit, "DiT model"),
            "vae": self._input(vae, "VAE model"),
            "text_encoder": self._input(text_encoder, "text encoder"),
        }
        from fizgig.repair_studio.state import SliderState
        normalized, engine = self._create_engine(family, model_paths, device, blocks_to_swap)
        engine.load_primary(paths["primary"])
        if paths["donor"]:
            engine.load_donor(paths["donor"])
        result = engine.generate_preview(SliderState.from_json(dict(state)))
        image = result.get("middle") if isinstance(result, dict) else result
        if image is None or not hasattr(image, "save"):
            raise RepairError("render engine returned no preview image")
        image.save(output_path)
        return {"output_relative_path": output_path.relative_to(self.paths.root).as_posix(), "family": normalized}

    def _create_engine(self, family: str, model_paths: Mapping[str, str], device: str, blocks_to_swap: int):
        normalized = str(family).strip().lower()
        if normalized in {"klein", "klein9b", "flux"}:
            from fizgig.repair_studio.engine import RepairEngine
            engine = RepairEngine()
            engine.ensure_pipeline(**model_paths, device=device, blocks_to_swap=int(blocks_to_swap))
        elif normalized in {"krea2", "krea"}:
            from fizgig.repair_studio.krea2_engine import Krea2RepairEngine
            engine = Krea2RepairEngine()
            engine.ensure_pipeline(turbo_path=model_paths["dit"], vae_path=model_paths["vae"], text_encoder_path=model_paths["text_encoder"], device=device, blocks_to_swap=int(blocks_to_swap))
        elif normalized in {"h3", "minimax", "minimaxh3"}:
            from fizgig.repair_studio.h3_engine import H3RepairEngine
            engine = H3RepairEngine()
            engine.ensure_pipeline(**model_paths, device=device)
        else:
            raise RepairError("family must be klein, krea2, or h3")
        return normalized, engine

    def render_explorer_variants(
        self,
        family: str,
        primary: str,
        output_dir: str,
        state: Mapping[str, Any],
        dit: str,
        vae: str,
        text_encoder: str,
        donor: str = "",
        device: str = "cuda",
        blocks_to_swap: int = 0,
        variants: int = 4,
        intensity: float = 0.5,
        structure: float = 1.0,
    ) -> dict[str, Any]:
        """Render human-guided Explorer mutations from one loaded engine."""
        self.validate_state(state)
        paths = {"primary": self._input(primary, "primary LoRA"), "donor": self._input(donor, "donor LoRA") if donor.strip() else ""}
        model_paths = {"dit": self._input(dit, "DiT model"), "vae": self._input(vae, "VAE model"), "text_encoder": self._input(text_encoder, "text encoder")}
        destination = self.paths.resolve_child(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        from fizgig.repair_studio.state import SliderState
        base = SliderState.from_json(dict(state))
        normalized, engine = self._create_engine(family, model_paths, device, blocks_to_swap)
        engine.load_primary(paths["primary"])
        if paths["donor"]:
            engine.load_donor(paths["donor"])
        active_blocks = set(getattr(engine, "primary_block_ids", set())) or set(base.blocks)
        count = max(1, min(int(variants), 8))
        images = []
        for index in range(count):
            variant = base.mutate(active_blocks, num_mutations=3, intensity=float(intensity), structure=float(structure))
            image = engine.generate_preview(variant)
            if isinstance(image, dict):
                image = image.get("middle")
            output = destination / f"variant-{index + 1:02d}.png"
            image.save(output)
            images.append({"index": index + 1, "relative_path": output.relative_to(self.paths.root).as_posix()})
        return {"family": normalized, "variants": images}

    def render_royale_checkpoints(
        self,
        family: str,
        folder: str,
        output_dir: str,
        dit: str,
        vae: str,
        text_encoder: str,
        prompt: str = "",
        seed: int = 42,
        width: int = 512,
        height: int = 512,
        device: str = "cuda",
        blocks_to_swap: int = 0,
        max_checkpoints: int = 32,
    ) -> dict[str, Any]:
        """Render a checkpoint sequence for Royale using one resident engine."""
        from fizgig.lora_royale.scan import scan_checkpoints
        root = self.paths.resolve_child(folder)
        if not root.is_dir():
            raise RepairError(f"checkpoint folder does not exist: {folder}")
        checkpoints = scan_checkpoints(str(root))[: max(1, min(int(max_checkpoints), 64))]
        if not checkpoints:
            raise RepairError("no SafeTensors checkpoints found")
        model_paths = {"dit": self._input(dit, "DiT model"), "vae": self._input(vae, "VAE model"), "text_encoder": self._input(text_encoder, "text encoder")}
        destination = self.paths.resolve_child(output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        from fizgig.repair_studio.state import SliderState
        state = SliderState.default_klein9b() if str(family).lower() in {"klein", "klein9b", "flux"} else (SliderState.default_krea2() if str(family).lower() in {"krea", "krea2"} else SliderState.default_h3())
        state.prompt, state.seed, state.preview_width, state.preview_height = str(prompt), int(seed), int(width), int(height)
        normalized, engine = self._create_engine(family, model_paths, device, blocks_to_swap)
        outputs = []
        for index, (label, checkpoint) in enumerate(checkpoints):
            if index == 0:
                engine.load_primary(checkpoint)
            elif not engine.swap_primary_weights(checkpoint):
                engine.reset()
                engine.load_primary(checkpoint)
            image = engine.generate_preview(state)
            if isinstance(image, dict):
                image = image.get("middle")
            output = destination / f"checkpoint-{index + 1:03d}.png"
            image.save(output)
            outputs.append({"label": str(label), "source_relative_path": Path(checkpoint).relative_to(self.paths.root).as_posix(), "relative_path": output.relative_to(self.paths.root).as_posix()})
        return {"family": normalized, "checkpoints": outputs}
