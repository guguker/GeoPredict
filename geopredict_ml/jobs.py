from __future__ import annotations

from dataclasses import dataclass, field
from threading import Lock, Thread
import time
import uuid
from typing import Any, Callable


@dataclass
class AnalysisJob:
    job_id: str
    status: str
    created_at: float
    updated_at: float
    result: dict[str, Any] | None = None
    error: str | None = None


class InMemoryAnalysisJobStore:
    def __init__(self) -> None:
        self._jobs: dict[str, AnalysisJob] = {}
        self._lock = Lock()

    def submit(
        self,
        payload: dict[str, Any],
        runner: Callable[[dict[str, Any]], dict[str, Any]],
        run_inline: bool = False,
    ) -> dict[str, Any]:
        now = time.time()
        job = AnalysisJob(job_id=str(uuid.uuid4()), status="queued", created_at=now, updated_at=now)
        with self._lock:
            self._jobs[job.job_id] = job

        if run_inline:
            self._run(job.job_id, payload, runner)
        else:
            Thread(target=self._run, args=(job.job_id, payload, runner), daemon=True).start()
        return self.get(job.job_id)

    def get(self, job_id: str) -> dict[str, Any]:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise KeyError(job_id)
            return {
                "job_id": job.job_id,
                "status": job.status,
                "created_at": job.created_at,
                "updated_at": job.updated_at,
                "result": job.result,
                "error": job.error,
            }

    def _run(
        self,
        job_id: str,
        payload: dict[str, Any],
        runner: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> None:
        self._update(job_id, status="running")
        try:
            result = runner(payload)
        except Exception as exc:
            self._update(job_id, status="failed", error=str(exc))
        else:
            self._update(job_id, status="done", result=result)

    def _update(
        self,
        job_id: str,
        status: str,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        with self._lock:
            job = self._jobs[job_id]
            job.status = status
            job.updated_at = time.time()
            job.result = result
            job.error = error
