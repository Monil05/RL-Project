"""Video jobs call the existing renderer in a background thread and store files by job id."""

from __future__ import annotations

import threading
import uuid
from pathlib import Path

from backend.app.bootstrap import GENERATED_DIR
from backend.app.services.config_factory import build_config, control_fingerprint
from backend.app.services.errors import ApiError

MAX_FRAMES = 400


class VideoService:
    def __init__(self, training_service, output_dir: Path = GENERATED_DIR) -> None:
        self._training = training_service
        self._output_dir = output_dir
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}

    def start(self, payload) -> dict:
        frames = payload.duration_seconds * payload.frames_per_step
        if frames > MAX_FRAMES:
            raise ApiError(
                422,
                f"This request would render {frames} frames. The existing exporter holds every frame in memory, so the API limit is {MAX_FRAMES} frames. Reduce duration or frames per step.",
            )
        config = build_config(
            scenario=payload.scenario,
            lane_count=payload.lane_count,
            free_left_turn=payload.free_left_turn,
            duration_seconds=payload.duration_seconds,
            seed=payload.seed,
        )
        agent = None
        if payload.algorithm != "Fixed Time":
            resolved = self._training.resolve_agent(
                payload.algorithm,
                control_fingerprint(config),
                payload.agent_job_id,
            )
            agent = resolved["agent"]
        with self._lock:
            if any(job["status"] in ("queued", "running") for job in self._jobs.values()):
                raise ApiError(409, "A video job is already queued or running.")
            job_id = uuid.uuid4().hex
            job = {
                "id": job_id,
                "status": "queued",
                "algorithm": payload.algorithm,
                "scenario": payload.scenario,
                "error": None,
                "filename": f"{job_id}.mp4",
            }
            self._jobs[job_id] = job
        threading.Thread(
            target=self._execute,
            args=(job_id, config, agent, payload),
            name=f"video-{job_id[:8]}",
            daemon=True,
        ).start()
        return self.status(job_id)

    def status(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(404, "Video job not found.")
            return _public(job)

    def file_path(self, job_id: str) -> Path:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(404, "Video job not found.")
            if job["status"] != "completed":
                raise ApiError(409, "Video is not ready.")
            path = self._output_dir / job["filename"]
        if not path.exists():
            raise ApiError(404, "Rendered file is missing.")
        return path

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(404, "Video job not found.")
            if job["status"] == "queued":
                job["status"] = "cancelled"
                return _public(job)
            if job["status"] == "running":
                raise ApiError(409, "Video rendering has started and cannot be interrupted safely.")
            raise ApiError(409, f"Job is already {job['status']}.")

    def _execute(self, job_id: str, config, agent, payload) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job["status"] == "cancelled":
                return
            job["status"] = "running"
            filename = job["filename"]
        try:
            from visualization.video_renderer import generate_simulation_video

            self._output_dir.mkdir(parents=True, exist_ok=True)
            generate_simulation_video(
                config,
                agent,
                payload.algorithm,
                output_path=str(self._output_dir / filename),
                fps=payload.fps,
                frames_per_step=payload.frames_per_step,
            )
        except Exception as exc:  # noqa: BLE001 - report renderer or missing-dependency failures
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["error"] = str(exc)
            return
        with self._lock:
            job = self._jobs[job_id]
            if job["status"] == "cancelled":
                return
            job["status"] = "completed"


def _public(job: dict) -> dict:
    ready = job["status"] == "completed"
    return {
        "id": job["id"],
        "status": job["status"],
        "algorithm": job["algorithm"],
        "scenario": job["scenario"],
        "error": job["error"],
        "download_url": f"/api/video/{job['id']}/file" if ready else None,
        "progress_available": False,
    }
