"""Header-only metadata inspection tests."""

import json
import tempfile
import unittest
from pathlib import Path

from fizgig.app.metadata import MetadataError, MetadataService


class MetadataServiceTests(unittest.TestCase):
    def test_reads_metadata_without_loading_tensor_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.safetensors"
            header = {"__metadata__": {"modelspec.title": "Demo"}, "layer.weight": {"dtype": "F32", "shape": [2, 3], "data_offsets": [0, 24]}}
            encoded = json.dumps(header).encode()
            path.write_bytes(len(encoded).to_bytes(8, "little") + encoded + b"unused tensor bytes")
            result = MetadataService(directory).inspect("model.safetensors")
            self.assertEqual(result["metadata"]["modelspec.title"], "Demo")
            self.assertEqual(result["tensor_count"], 1)
            self.assertEqual(result["tensors"][0]["shape"], [2, 3])

    def test_rejects_non_safetensors(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.bin"
            path.write_bytes(b"x")
            with self.assertRaises(MetadataError):
                MetadataService(directory).inspect(str(path))


if __name__ == "__main__":
    unittest.main()
