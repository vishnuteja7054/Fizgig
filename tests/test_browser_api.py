"""HTTP contract tests for the browser adapter.

These tests intentionally exercise the FastAPI application through a real
loopback Uvicorn process rather than only calling the underlying services.
Install requirements-web.txt before running them.
"""

from __future__ import annotations

import json
import os
import socket
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

try:
    import uvicorn  # noqa: F401
except ModuleNotFoundError as exc:  # pragma: no cover - optional test dependency
    raise unittest.SkipTest(f"browser API dependencies are not installed: {exc}")


class BrowserApiTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        self.port = self._free_port()
        self._start_server(token=None)
        self._wait_for_health()

    def tearDown(self) -> None:
        self.process.terminate()
        try:
            self.process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.process.kill()
            self.process.wait(timeout=5)
        self.tempdir.cleanup()

    @staticmethod
    def _free_port() -> int:
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            return int(sock.getsockname()[1])

    def _start_server(self, token: str | None) -> None:
        environment = os.environ.copy()
        environment["FIZGIG_WORKSPACE_ROOT"] = str(self.root)
        if token is None:
            environment.pop("FIZGIG_API_TOKEN", None)
        else:
            environment["FIZGIG_API_TOKEN"] = token
        source_root = str(Path(__file__).resolve().parents[1] / "src")
        environment["PYTHONPATH"] = source_root + os.pathsep + environment.get("PYTHONPATH", "")
        self.process = subprocess.Popen(
            [
                os.environ.get("PYTHON", sys.executable),
                "-m",
                "uvicorn",
                "fizgig.web.app:app",
                "--host",
                "127.0.0.1",
                "--port",
                str(self.port),
            ],
            env=environment,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        self.base_url = f"http://127.0.0.1:{self.port}"

    def _wait_for_health(self) -> None:
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            try:
                response = self._request("/api/health")
                if response[0] == 200:
                    return
            except OSError:
                pass
            time.sleep(0.1)
        self.fail("Uvicorn did not become ready")

    def _request(self, path: str, *, headers: dict[str, str] | None = None) -> tuple[int, bytes]:
        try:
            with urlopen(Request(self.base_url + path, headers=headers or {}), timeout=5) as response:
                return response.status, response.read()
        except HTTPError as error:
            return error.code, error.read()

    def test_health_and_repair_state_are_http_accessible(self) -> None:
        status, body = self._request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(json.loads(body)["status"], "ok")

        status, body = self._request("/api/repair/default-state?family=klein")
        self.assertEqual(status, 200)
        payload = json.loads(body)
        self.assertEqual(payload["family"], "klein")
        self.assertGreater(len(payload["state"]["blocks"]), 0)

    def test_artifacts_are_workspace_safe(self) -> None:
        artifact = self.root / "out" / "result.txt"
        artifact.parent.mkdir()
        artifact.write_text("browser artifact", encoding="utf-8")

        status, body = self._request("/api/artifacts/download?path=out/result.txt")
        self.assertEqual(status, 200)
        self.assertEqual(body, b"browser artifact")

        status, _ = self._request("/api/artifacts/download?path=../outside.txt")
        self.assertEqual(status, 400)

    def test_optional_bearer_auth_protects_api_but_not_health(self) -> None:
        self.process.terminate()
        self.process.wait(timeout=5)
        # Avoid TIME_WAIT/reuse races when replacing the unauthenticated server.
        self.port = self._free_port()
        self._start_server(token="test-token")
        self._wait_for_health()
        self.assertEqual(self._request("/api/health")[0], 200)
        self.assertEqual(self._request("/api/jobs")[0], 401)
        self.assertEqual(
            self._request("/api/jobs", headers={"Authorization": "Bearer test-token"})[0],
            200,
        )


if __name__ == "__main__":
    unittest.main()
