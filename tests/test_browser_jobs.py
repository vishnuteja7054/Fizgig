"""Persistent job service tests without model dependencies."""

import tempfile
import time
import unittest

from fizgig.app.jobs import JobService


class JobServiceTests(unittest.TestCase):
    @staticmethod
    def _wait(service: JobService, job_id: str):
        for _ in range(100):
            record = service.get(job_id)
            if record.status in {"completed", "failed", "cancelled"}:
                return record
            time.sleep(0.01)
        raise AssertionError("job did not finish")

    def test_job_state_is_persisted_until_completion(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = JobService(directory)
            record = service.create("test", {"value": 4}, lambda context, payload: payload["value"] * 2)
            finished = self._wait(service, record.id)
            self.assertEqual(finished.status, "completed")
            self.assertEqual(finished.result, 8)
            self.assertEqual(service.get(record.id).result, 8)

    def test_worker_failures_are_recorded(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = JobService(directory)
            record = service.create("test", {}, lambda _context, _payload: 1 / 0)
            finished = self._wait(service, record.id)
            self.assertEqual(finished.status, "failed")
            self.assertIn("ZeroDivisionError", finished.error or "")

    def test_cancellation_request_is_observed(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            service = JobService(directory)

            def worker(context, _payload):
                for _ in range(100):
                    context.raise_if_cancelled()
                    time.sleep(0.01)
                return "done"

            record = service.create("test", {}, worker)
            service.cancel(record.id)
            finished = self._wait(service, record.id)
            self.assertEqual(finished.status, "cancelled")


if __name__ == "__main__":
    unittest.main()
