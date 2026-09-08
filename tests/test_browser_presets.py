"""Compatibility and safety tests for the browser-facing preset repository."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.presets import (
    PresetError,
    PresetExistsError,
    PresetNotFoundError,
    PresetRepository,
)


class PresetRepositoryTests(unittest.TestCase):
    def test_save_list_load_and_delete_use_existing_layout(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = PresetRepository(directory)
            values = {"LEARNING_RATE": 0.0001, "NETWORK_DIM": 16}
            path = repo.save("Krea 2", "identity", values)
            self.assertEqual(path, Path(directory) / "presets" / "Krea 2" / "identity.json")
            self.assertEqual(repo.list("Krea 2"), ["identity"])
            self.assertEqual(repo.load("Krea 2", "identity"), values)
            repo.delete("Krea 2", "identity")
            self.assertEqual(repo.list("Krea 2"), [])

    def test_overwrite_must_be_explicit(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = PresetRepository(directory)
            repo.save("Klein", "run", {"x": 1})
            with self.assertRaises(PresetExistsError):
                repo.save("Klein", "run", {"x": 2})
            repo.save("Klein", "run", {"x": 2}, overwrite=True)
            self.assertEqual(repo.load("Klein", "run"), {"x": 2})

    def test_invalid_names_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = PresetRepository(directory)
            for bad in ("../outside", "a/b", "a\\b", ""):
                with self.assertRaises(PresetError):
                    repo.save("Klein", bad, {})
            with self.assertRaises(PresetError):
                repo.save("../outside", "valid", {})

    def test_missing_and_non_object_presets_are_reported(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            repo = PresetRepository(directory)
            with self.assertRaises(PresetNotFoundError):
                repo.load("Klein", "missing")
            path = Path(directory) / "presets" / "Klein" / "broken.json"
            path.parent.mkdir(parents=True)
            path.write_text("[]", encoding="utf-8")
            with self.assertRaises(PresetError):
                repo.load("Klein", "broken")


if __name__ == "__main__":
    unittest.main()
