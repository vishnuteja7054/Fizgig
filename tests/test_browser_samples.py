"""Sample artifact tests without model dependencies."""

import tempfile
import unittest
from pathlib import Path

from fizgig.app.samples import SampleError, SampleService


class SampleServiceTests(unittest.TestCase):
    def test_writes_desktop_compatible_prompt_file(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SampleService(directory)
            result = service.write_prompts("subject.txt", "# note\nA portrait\n\nA landscape")
            self.assertEqual(result["count"], 2)
            self.assertEqual((Path(directory) / "samples" / "subject.txt").read_text(), "A portrait\nA landscape\n")

    def test_override_is_atomic_and_clearable(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SampleService(directory)
            result = service.write_override("output_loras", prompt="A portrait", seed=7)
            self.assertEqual(result["seed"], 7)
            self.assertTrue((Path(directory) / "output_loras" / ".sample_override.json").is_file())
            service.clear_override("output_loras")
            self.assertFalse((Path(directory) / "output_loras" / ".sample_override.json").exists())

    def test_rejects_empty_prompts_and_unsafe_names(self):
        with tempfile.TemporaryDirectory() as directory:
            service = SampleService(directory)
            with self.assertRaises(SampleError):
                service.write_prompts("../prompts.txt", "hello")
            with self.assertRaises(SampleError):
                service.write_prompts("prompts.txt", "# only comments")


if __name__ == "__main__":
    unittest.main()
