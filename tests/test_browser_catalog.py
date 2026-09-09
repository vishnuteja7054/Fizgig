"""Catalog tests for browser Explorer/Royale file selection."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.catalog import LoraCatalogService


class CatalogTests(unittest.TestCase):
    def test_explorer_and_royale_catalogs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "output_loras"
            root.mkdir()
            for name in ("subject-000001.safetensors", "subject-000002.safetensors"):
                (root / name).write_bytes(b"x")
            service = LoraCatalogService(directory)
            self.assertEqual(len(service.explorer()), 2)
            self.assertEqual([item["label"] for item in service.royale()], ["1", "2"])


if __name__ == "__main__":
    unittest.main()
