"""Training dataset config tests without model dependencies."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.training_config import (
    DatasetConfigRequest,
    TrainingConfigError,
    TrainingConfigService,
)


class TrainingConfigServiceTests(unittest.TestCase):
    def test_build_matches_training_toml_shape(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dataset" / "subject").mkdir(parents=True)
            output, content = TrainingConfigService(root).build(DatasetConfigRequest(
                name="subject_run",
                folder="dataset/subject",
                target_megapixels=1.0,
                batch_size=2,
            ))
            self.assertEqual(output, root / "dataset" / "subject_run.toml")
            self.assertIn("resolution = [992, 992]", content)
            self.assertIn('image_directory = "' + str((root / "dataset" / "subject").resolve()) + '"', content)
            self.assertIn("batch_size = 2", content)
            self.assertTrue(output.is_file())

    def test_dataset_and_cache_paths_stay_inside_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dataset" / "subject").mkdir(parents=True)
            service = TrainingConfigService(root)
            with self.assertRaises(ValueError):
                service.build(DatasetConfigRequest(folder="../outside"))
            with self.assertRaises(ValueError):
                service.build(DatasetConfigRequest(folder="dataset/subject", cache_root="../cache"))

    def test_invalid_values_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "dataset").mkdir()
            service = TrainingConfigService(root)
            with self.assertRaises(TrainingConfigError):
                service.build(DatasetConfigRequest(name="bad/name"))
            with self.assertRaises(TrainingConfigError):
                service.build(DatasetConfigRequest(target_megapixels=0))
            with self.assertRaises(TrainingConfigError):
                service.build(DatasetConfigRequest(batch_size=0))


if __name__ == "__main__":
    unittest.main()
