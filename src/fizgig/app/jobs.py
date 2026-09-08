"""Small persistent job service for browser-triggered long-running work."""

from __future__ import annotations

import json
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from fizgig.app.state import JsonObject, JsonStateStore, WorkspacePaths


ACTIVE_STATUSES = frozenset({"queued", "starting", "running", "cancel_requested"})


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class JobCancelled(Exception):
    """Raised internally when a worker observes a cancellation request."""


@dataclass(frozen=True)
class JobRecord:
    id: str
    kind: str
    status: str
    progress: float
    message: str
    payload: dict[str, Any]
    result: Any = None
    error: str | None = None
    created_at: str = ""
    started_at: str | None = None
    finished_at: str | None = None
    cancel_requested: bool = False

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "JobRecord":
        return cls(
            id=str(value["id"]),
            kind=str(value["kind"]),
            status=str(value["status"]),
            progress=float(value.get("progress", 0)),
            message=str(value.get("message", "")),
            payload=dict(value.get("payload", {})),
            result=value.get("result"),
            error=value.get("error"),
            created_at=str(value.get("created_at", "")),
            started_at=value.get("started_at"),
            finished_at=value.get("finished_at"),
            cancel_requested=bool(value.get("cancel_requested", False)),
        )

    def as_dict(self) -> JsonObject:
        return {
            "id": self.id,
            "kind": self.kind,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "payload": self.payload,
            "result": self.result,
            "error": self.error,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "cancel_requested": self.cancel_requested,
        }


class JobContext:
    def __init__(self, service: "JobService", job_id: str) -> None:
        self.service = service
        self.job_id = job_id

    def update(self, *, progress: float | None = None, message: str | None = None) -> None:
        self.service._update(self.job_id, progress=progress, message=message, status="running")

    def raise_if_cancelled(self) -> None:
        if self.service.get(self.job_id).cancel_requested:
            raise JobCancelled()


Worker = Callable[[JobContext, dict[str, Any]], Any]


class JobService:
    """Persist job state to JSON and execute registered work off the API thread."""

    def __init__(self, workspace_root: str | Path, *, max_workers: int = 2) -> None:
        paths = WorkspacePaths(workspace_root)
        self.jobs_root = paths.resolve_child(".fizgig/jobs")
        self.jobs_root.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._executor = ThreadPoolExecutor(max_workers=max_workers, thread_name_prefix="fizgig-job")
        self._recover_interrupted()

    def create(self, kind: str, payload: Mapping[str, Any], worker: Worker) -> JobRecord:
        if not kind or "/" in kind or "\\" in kind:
            raise ValueError("job kind is invalid")
        job_id = uuid.uuid4().hex
        record = JobRecord(
            id=job_id, kind=kind, status="queued", progress=0, message="Queued",
            payload=dict(payload), created_at=_now(),
        )
        self._save(record)
        self._executor.submit(self._run, record, worker)
        return record

    def get(self, job_id: str) -> JobRecord:
        path = self._path(job_id)
        try:
            return JobRecord.from_dict(json.loads(path.read_text(encoding="utf-8")))
        except FileNotFoundError as exc:
            raise KeyError(f"job not found: {job_id}") from exc
        except (OSError, json.JSONDecodeError, KeyError, TypeError, ValueError) as exc:
            raise ValueError(f"job record is unreadable: {job_id}") from exc

    def list(self, *, limit: int = 50) -> list[JobRecord]:
        records: list[JobRecord] = []
        for path in sorted(self.jobs_root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True):
            try:
                records.append(self.get(path.stem))
            except (KeyError, ValueError, OSError):
                continue
            if len(records) >= max(1, min(limit, 200)):
                break
        return records

    def cancel(self, job_id: str) -> JobRecord:
        record = self.get(job_id)
        if record.status in ACTIVE_STATUSES:
            return self._update(job_id, status="cancel_requested", message="Cancellation requested", cancel_requested=True)
        return record

    def _run(self, record: JobRecord, worker: Worker) -> None:
        self._update(record.id, status="starting", message="Starting", started_at=_now())
        try:
            context = JobContext(self, record.id)
            context.raise_if_cancelled()
            result = worker(context, record.payload)
            context.raise_if_cancelled()
            self._update(record.id, status="completed", progress=100, message="Completed", result=result, finished_at=_now())
        except JobCancelled:
            self._update(record.id, status="cancelled", message="Cancelled", finished_at=_now())
        except Exception as exc:  # job failures belong in the record, not the server process
            self._update(record.id, status="failed", message="Failed", error=f"{type(exc).__name__}: {exc}", finished_at=_now())

    def _recover_interrupted(self) -> None:
        for record in self.list(limit=200):
            if record.status in ACTIVE_STATUSES:
                self._update(record.id, status="failed", message="Interrupted by server restart", error="job interrupted by server restart", finished_at=_now())

    def _update(self, job_id: str, **changes: Any) -> JobRecord:
        with self._lock:
            record = self.get(job_id)
            values = record.as_dict()
            values.update({key: value for key, value in changes.items() if value is not None})
            updated = JobRecord.from_dict(values)
            self._save(updated)
            return updated

    def _save(self, record: JobRecord) -> None:
        with self._lock:
            JsonStateStore(self._path(record.id)).save(record.as_dict())

    def _path(self, job_id: str) -> Path:
        if not job_id or Path(job_id).name != job_id or not all(char.isalnum() for char in job_id):
            raise KeyError(f"job id is invalid: {job_id}")
        return self.jobs_root / f"{job_id}.json"
