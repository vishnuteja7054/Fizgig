"""Repair state tests that avoid importing torch/bake code."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.repair import RepairError, RepairService


class RepairServiceTests(unittest.TestCase):
    def test_default_state_has_klein_block_grid(self):
        state = RepairService.default_state()
        self.assertEqual(len(state["blocks"]), 32)
        self.assertIn("double_0", state["blocks"])
        self.assertIn("single_23", state["blocks"])

    def test_default_state_supports_all_engine_families_without_torch(self):
        self.assertEqual(len(RepairService.default_state("krea2")["blocks"]), 32)
        self.assertEqual(len(RepairService.default_state("h3")["blocks"]), 52)

    def test_render_state_rejects_non_image_output(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "primary.safetensors").write_bytes(b"x")
            service = RepairService(directory)
            with self.assertRaises(RepairError):
                service.render_preview(
                    "klein", "primary.safetensors", "out/preview.txt",
                    service.default_state(), "/missing/dit", "/missing/vae", "/missing/te",
                )

    def test_validation_requires_workspace_safe_output_and_existing_primary(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "primary.safetensors").write_bytes(b"x")
            service = RepairService(directory)
            with self.assertRaises(RepairError):
                service.validate("primary.safetensors", "../escape.safetensors", RepairService.default_state())


if __name__ == "__main__":
    unittest.main()
