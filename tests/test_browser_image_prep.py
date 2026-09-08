"""Image preparation service tests without model or GUI dependencies."""

import tempfile
import unittest
from pathlib import Path

from PIL import Image

from fizgig.app.image_prep import ImagePrepService


class ImagePrepServiceTests(unittest.TestCase):
    def test_resize_only_preserves_caption_and_moves_original(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "set"
            folder.mkdir()
            Image.new("RGB", (2048, 1024), "red").save(folder / "photo.jpg")
            (folder / "photo.txt").write_text("subject", encoding="utf-8")

            result = ImagePrepService(root).resize_only("set", 1.0)

            self.assertEqual(result.converted, 1)
            self.assertEqual(result.errors, 0)
            self.assertTrue((folder / "photo.png").is_file())
            self.assertTrue((folder / "originals" / "photo.jpg").is_file())
            self.assertEqual((folder / "photo.txt").read_text(encoding="utf-8"), "subject")
            with Image.open(folder / "photo.png") as image:
                self.assertLessEqual(image.width * image.height, result.target_area)
                self.assertEqual(image.width % 16, 0)
                self.assertEqual(image.height % 16, 0)

    def test_small_png_is_skipped_and_replace_mode_removes_source(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "set"
            folder.mkdir()
            Image.new("RGB", (256, 256), "blue").save(folder / "small.png")
            Image.new("RGB", (2048, 1024), "green").save(folder / "large.jpg")

            result = ImagePrepService(root).resize_only("set", 1.0, replace_originals=True)

            self.assertEqual(result.skipped, 1)
            self.assertEqual(result.converted, 1)
            self.assertTrue((folder / "small.png").is_file())
            self.assertTrue((folder / "large.png").is_file())
            self.assertFalse((folder / "large.jpg").exists())
            self.assertFalse((folder / "originals").exists())

    def test_output_collision_gets_a_suffix(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            folder = root / "set"
            folder.mkdir()
            Image.new("RGB", (2048, 1024), "red").save(folder / "photo.jpg")
            Image.new("RGB", (256, 256), "blue").save(folder / "photo.png")

            result = ImagePrepService(root).resize_only("set", 1.0)

            outputs = [item.output_relative_path for item in result.files if item.status == "converted"]
            self.assertIn("set/photo_2.png", outputs)
            self.assertTrue((folder / "photo.png").is_file())

    def test_target_megapixels_are_validated(self) -> None:
        with self.assertRaises(ValueError):
            ImagePrepService.target_area_for_megapixels(0)
        with self.assertRaises(ValueError):
            ImagePrepService.target_area_for_megapixels(101)


if __name__ == "__main__":
    unittest.main()
