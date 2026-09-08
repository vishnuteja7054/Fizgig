"""Workspace state tests without GUI or model dependencies."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.workspace import WorkspaceStateError, WorkspaceStateService


class WorkspaceStateServiceTests(unittest.TestCase):
    def test_defaults_and_existing_desktop_keys_are_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / ".last_used.json"
            path.write_text('{"architecture": "Krea 2", "desktop_only": 7}\n', encoding="utf-8")
            state = WorkspaceStateService(directory).load()
            self.assertEqual(state["architecture"], "Krea 2")
            self.assertEqual(state["desktop_only"], 7)
            self.assertEqual(state["dataset_folder"], "dataset")

    def test_update_merges_browser_values_atomically(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = WorkspaceStateService(directory)
            state = service.update({"dataset_folder": "dataset/person", "prep_megapixels": "2.0"})
            self.assertEqual(state["dataset_folder"], "dataset/person")
            self.assertEqual(service.load()["prep_megapixels"], "2.0")

    def test_nested_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(WorkspaceStateError):
                WorkspaceStateService(directory).update({"bad": {"nested": True}})


if __name__ == "__main__":
    unittest.main()
