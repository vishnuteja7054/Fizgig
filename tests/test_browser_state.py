"""Frontend-neutral workspace and JSON state tests.

These tests use only the standard library so they can run before the full GPU
environment is installed.
"""

import json
import tempfile
import unittest
from pathlib import Path

from fizgig.app.state import JsonStateStore, WorkspacePaths


class WorkspacePathsTests(unittest.TestCase):
    def test_relative_path_is_resolved_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspacePaths(directory)
            self.assertEqual(workspace.resolve_child("dataset/a.jpg"),
                             Path(directory).resolve() / "dataset/a.jpg")

    def test_escape_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspacePaths(directory)
            with self.assertRaises(ValueError):
                workspace.resolve_child("../outside.txt")

    def test_portable_paths_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspacePaths(directory)
            child = Path(directory) / "output_loras"
            stored = workspace.relative_or_absolute(child)
            self.assertEqual(stored, "output_loras")
            self.assertEqual(Path(workspace.resolve_stored_path(stored)), child)

    def test_external_path_stays_absolute(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            workspace = WorkspacePaths(directory)
            external = Path(tempfile.gettempdir()) / "fizgig-model.safetensors"
            stored = workspace.relative_or_absolute(external)
            self.assertTrue(Path(stored).is_absolute())


class JsonStateStoreTests(unittest.TestCase):
    def test_defaults_and_saved_values_are_merged(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(json.dumps({"image_folder": "/data/images"}), encoding="utf-8")
            state = JsonStateStore(path).load({"image_folder": "", "trigger": "word"})
            self.assertEqual(state, {"image_folder": "/data/images", "trigger": "word"})

    def test_invalid_json_falls_back_to_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{broken", encoding="utf-8")
            self.assertEqual(JsonStateStore(path).load({"ok": True}), {"ok": True})

    def test_save_is_readable_after_atomic_replace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "nested" / "state.json"
            JsonStateStore(path).save({"epoch": 4})
            self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {"epoch": 4})
            self.assertFalse(path.with_name("state.json.tmp").exists())


if __name__ == "__main__":
    unittest.main()
