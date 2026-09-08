"""Training command tests that do not import torch or require a GPU."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.training import TrainingCommandService, TrainingLaunchError, TrainingLaunchRequest


class TrainingCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "dataset").mkdir()
        (self.root / "dataset" / "train.toml").write_text("[general]\n", encoding="utf-8")
        for name in ("klein.safetensors", "vae.safetensors", "text_encoder.safetensors", "base.safetensors"):
            (self.root / name).write_bytes(b"placeholder")
        self.service = TrainingCommandService(self.root, project_root=self.root)

    def tearDown(self):
        self.temp.cleanup()

    def test_klein_matches_desktop_contract(self):
        command = self.service.build(TrainingLaunchRequest(
            architecture="Flux 2 Klein Base 9B",
            dataset_config="dataset/train.toml",
            dit="klein.safetensors",
            vae="vae.safetensors",
            text_encoder="text_encoder.safetensors",
            output_name="subject",
            quantize_4bit=True,
        ))
        self.assertEqual(command[:4], ["accelerate", "launch", "--num_cpu_threads_per_process", "2"])
        self.assertIn("--model_version", command)
        self.assertIn("klein-base-9b", command)
        self.assertIn("--network_module", command)
        self.assertIn("fizgig.networks.lora_klein", command)
        self.assertIn("--quant_4bit", command)
        self.assertNotIn("--fp8_base", command)

    def test_krea_and_minimax_use_native_entrypoints(self):
        for architecture, script in (("Krea 2", "krea2_train.py"), ("MiniMax H3", "minimax_train.py")):
            command = self.service.build(TrainingLaunchRequest(
                architecture=architecture,
                dataset_config="dataset/train.toml",
                dit="base.safetensors",
                output_name="subject",
                blocks_to_swap="auto" if architecture == "MiniMax H3" else 4,
            ))
            self.assertEqual(command[0], self.service.python_executable)
            self.assertTrue(command[1].endswith(f"src/fizgig/scripts/{script}"))
            self.assertIn("--dataset_config", command)
            self.assertIn("--output_name", command)

    def test_workspace_outputs_cannot_escape(self):
        with self.assertRaises(TrainingLaunchError):
            self.service.build(TrainingLaunchRequest(
                architecture="Krea 2",
                dataset_config="dataset/train.toml",
                dit="base.safetensors",
                output_dir="../outside",
            ))

    def test_preview_is_shell_safe_and_does_not_execute(self):
        result = self.service.preview(TrainingLaunchRequest(
            architecture="Krea 2",
            dataset_config="dataset/train.toml",
            dit="base.safetensors",
            output_name="name with spaces",
        ))
        self.assertTrue(result["execution_ready"])
        self.assertIn("'name with spaces'", result["shell_command"])


if __name__ == "__main__":
    unittest.main()
