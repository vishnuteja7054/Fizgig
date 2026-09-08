"""Dataset and caption service tests without model or GUI dependencies."""

import tempfile
import unittest
from io import BytesIO
from pathlib import Path

from fizgig.app.dataset import DatasetService


class DatasetServiceTests(unittest.TestCase):
    def test_scan_is_top_level_and_classifies_media(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "set").mkdir()
            (root / "set" / "a.JPG").write_bytes(b"image")
            (root / "set" / "clip.mp4").write_bytes(b"video")
            (root / "set" / "voice.wav").write_bytes(b"audio")
            (root / "set" / "notes.md").write_text("ignore", encoding="utf-8")
            (root / "set" / "removed").mkdir()
            (root / "set" / "removed" / "old.jpg").write_bytes(b"removed")
            (root / "set" / "a.txt").write_text("subject", encoding="utf-8")

            items = DatasetService(root).scan("set")
            self.assertEqual([item.relative_path for item in items],
                             ["set/a.JPG", "set/clip.mp4", "set/voice.wav"])
            self.assertEqual([item.kind for item in items], ["image", "video", "audio"])
            self.assertTrue(items[0].has_caption)
            self.assertFalse(items[1].has_caption)

    def test_caption_round_trip_and_empty_caption_rejection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "set").mkdir()
            media = root / "set" / "photo.png"
            media.write_bytes(b"image")
            service = DatasetService(root)
            service.write_caption("set/photo.png", "a portrait")
            self.assertEqual(service.read_caption("set/photo.png"), "a portrait")
            with self.assertRaises(ValueError):
                service.write_caption("set/photo.png", "  ")

    def test_import_file_copies_supported_uploads_without_overwriting(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = DatasetService(directory)
            imported = service.import_file("set", "local/photo.png", BytesIO(b"image"))
            self.assertEqual(imported, "set/photo.png")
            self.assertEqual((Path(directory) / "set" / "photo.png").read_bytes(), b"image")
            with self.assertRaises(FileExistsError):
                service.import_file("set", "photo.png", BytesIO(b"replacement"))
            with self.assertRaises(ValueError):
                service.import_file("set", "photo.exe", BytesIO(b"bad"))

    def test_move_to_removed_preserves_media_and_caption(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "set").mkdir()
            (root / "set" / "photo.png").write_bytes(b"image")
            (root / "set" / "photo.txt").write_text("caption", encoding="utf-8")
            service = DatasetService(root)
            result = service.move_to_removed("set/photo.png")
            self.assertEqual(result, ("set/removed/photo.png", "set/removed/photo.txt"))
            self.assertTrue((root / "set" / "removed" / "photo.png").is_file())
            self.assertTrue((root / "set" / "removed" / "photo.txt").is_file())

    def test_move_to_removed_avoids_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "set" / "removed").mkdir(parents=True)
            (root / "set" / "photo.png").write_bytes(b"new")
            (root / "set" / "removed" / "photo.png").write_bytes(b"old")
            service = DatasetService(root)
            self.assertEqual(service.move_to_removed("set/photo.png")[0],
                             "set/removed/photo_1.png")

    def test_find_replace_preview_and_apply_are_literal(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "set").mkdir()
            caption = root / "set" / "photo.txt"
            caption.write_text("A path C:\\temp\\x and a PATH", encoding="utf-8")
            service = DatasetService(root)
            preview = service.find_replace("set", "path", r"C:\\new", apply=False)
            self.assertEqual(len(preview), 1)
            self.assertIn(r"C:\\new", preview[0]["new"])
            self.assertIn("C:\\temp\\x", caption.read_text(encoding="utf-8"))
            service.find_replace("set", "path", "replacement", apply=True)
            self.assertNotIn("path", caption.read_text(encoding="utf-8").lower())

    def test_paths_cannot_escape_workspace(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = DatasetService(directory)
            with self.assertRaises(ValueError):
                service.scan("../outside")


if __name__ == "__main__":
    unittest.main()
