"""Workbench command tests without torch/GPU dependencies."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.workbench import ExtractRequest, ProfileRequest, WorkbenchCommandService, WorkbenchError


class WorkbenchCommandTests(unittest.TestCase):
    def test_profile_krea2_is_weight_only(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "subject.safetensors").write_bytes(b"x")
            command = WorkbenchCommandService(root, project_root=root).profile(ProfileRequest(lora="subject.safetensors"))
            self.assertIn("--krea2", command)
            self.assertNotIn("--dit", command)

    def test_extract_weight_only_requires_no_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "subject.safetensors").write_bytes(b"x")
            command = WorkbenchCommandService(root, project_root=root).extract(ExtractRequest(source="subject.safetensors"))
            self.assertIn("--samples", command)
            self.assertIn("0", command)
            self.assertNotIn("--dit", command)

    def test_output_cannot_escape_workspace(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "subject.safetensors").write_bytes(b"x")
            with self.assertRaises(WorkbenchError):
                WorkbenchCommandService(root).profile(ProfileRequest(lora="subject.safetensors", output="../profile.html"))


if __name__ == "__main__":
    unittest.main()
