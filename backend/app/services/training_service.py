"""Background training jobs that call the existing train_q_learning and train_sarsa functions."""

from __future__ import annotations

import threading
import uuid

from backend.app.services.config_factory import build_config, control_fingerprint, public_config
from backend.app.services.errors import ApiError
from training.train import train_q_learning, train_sarsa


class TrainingService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._jobs: dict[str, dict] = {}

    def start(self, payload) -> dict:
        config = build_config(
            scenario=payload.scenario,
            lane_count=payload.lane_count,
            free_left_turn=payload.free_left_turn,
            duration_seconds=payload.duration_seconds,
            seed=payload.seed,
            episodes=payload.episodes,
            learning_rate=payload.learning_rate,
            discount_factor=payload.discount_factor,
            epsilon=payload.epsilon,
            epsilon_decay=payload.epsilon_decay,
            minimum_epsilon=payload.minimum_epsilon,
        )
        with self._lock:
            if any(job["status"] in ("queued", "running") for job in self._jobs.values()):
                raise ApiError(409, "A training job is already queued or running.")
            job_id = uuid.uuid4().hex
            job = {
                "id": job_id,
                "status": "queued",
                "algorithm": payload.algorithm,
                "scenario": payload.scenario,
                "seed": payload.seed,
                "config": config,
                "fingerprint": control_fingerprint(config),
                "public_config": public_config(config),
                "history": None,
                "summary": None,
                "agent": None,
                "error": None,
            }
            self._jobs[job_id] = job
        self._spawn(job_id)
        return self.status(job_id)

    def _spawn(self, job_id: str) -> None:
        threading.Thread(target=self._execute, args=(job_id,), name=f"train-{job_id[:8]}", daemon=True).start()

    def status(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(404, "Training job not found.")
            return _public_job(job)

    def list_jobs(self) -> list[dict]:
        with self._lock:
            return [_public_job(job) for job in self._jobs.values()]

    def list_agents(self) -> list[dict]:
        with self._lock:
            return [_public_job(job) for job in self._jobs.values() if job["status"] == "completed" and job["agent"] is not None]

    def cancel(self, job_id: str) -> dict:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise ApiError(404, "Training job not found.")
            if job["status"] == "queued":
                job["status"] = "cancelled"
                return _public_job(job)
            if job["status"] == "running":
                raise ApiError(
                    409,
                    "Training has entered the existing training function and cannot be interrupted safely.",
                )
            raise ApiError(409, f"Job is already {job['status']}.")

    def resolve_agent(self, algorithm: str, fingerprint: dict, job_id: str | None) -> dict:
        with self._lock:
            if job_id is not None:
                job = self._jobs.get(job_id)
                if job is None or job["status"] != "completed" or job["agent"] is None:
                    raise ApiError(409, "The selected training job is not a completed agent.")
                if job["algorithm"] != algorithm:
                    raise ApiError(409, "The selected agent was trained with a different algorithm.")
                if job["fingerprint"] != fingerprint:
                    raise ApiError(
                        409,
                        "The selected agent was trained on a different scenario, lane layout, or learning-rate configuration.",
                    )
                return {"agent": job["agent"], "meta": _agent_meta(job)}
            matches = [
                job
                for job in self._jobs.values()
                if job["status"] == "completed"
                and job["agent"] is not None
                and job["algorithm"] == algorithm
                and job["fingerprint"] == fingerprint
            ]
            if not matches:
                raise ApiError(
                    409,
                    f"No completed {algorithm} agent matches this scenario and learning configuration. Train one in the Training Centre first.",
                )
            job = matches[-1]
            return {"agent": job["agent"], "meta": _agent_meta(job)}

    def _execute(self, job_id: str) -> None:
        with self._lock:
            job = self._jobs[job_id]
            if job["status"] == "cancelled":
                return
            job["status"] = "running"
            algorithm = job["algorithm"]
            config = job["config"]
            seed = job["seed"]
        try:
            if algorithm == "Q-Learning":
                agent, history = train_q_learning(config, seed)
            else:
                agent, history = train_sarsa(config, seed)
        except Exception as exc:  # noqa: BLE001 - surface trainer failures to the client
            with self._lock:
                job = self._jobs[job_id]
                job["status"] = "failed"
                job["error"] = str(exc)
            return
        with self._lock:
            job = self._jobs[job_id]
            if job["status"] == "cancelled":
                return
            job["agent"] = agent
            job["history"] = history
            job["summary"] = _summary(history)
            job["status"] = "completed"


def _summary(history: list[dict]) -> dict:
    rewards = [float(row["reward"]) for row in history]
    return {
        "episodes": len(history),
        "last_episode_reward": rewards[-1] if rewards else None,
        "sum_of_episode_rewards": sum(rewards) if rewards else None,
        "last_average_waiting_time": float(history[-1]["average_waiting_time"]) if history else None,
        "last_throughput": int(history[-1]["throughput"]) if history else None,
        "last_epsilon": float(history[-1]["epsilon"]) if history else None,
        "training_time_seconds": history[-1].get("training_time_seconds") if history else None,
    }


def _agent_meta(job: dict) -> dict:
    learning = job["public_config"]["learning"]
    return {
        "job_id": job["id"],
        "algorithm": job["algorithm"],
        "scenario": job["scenario"],
        "seed": job["seed"],
        "episodes": learning["episodes"],
        "duration_seconds": job["public_config"]["simulation"]["duration_seconds"],
    }


def _public_job(job: dict) -> dict:
    return {
        "id": job["id"],
        "status": job["status"],
        "algorithm": job["algorithm"],
        "scenario": job["scenario"],
        "seed": job["seed"],
        "config": job["public_config"],
        "history": job["history"],
        "summary": job["summary"],
        "error": job["error"],
        "current_episode": None if job["status"] in ("queued", "running") else (len(job["history"]) if job["history"] else None),
        "progress_available": job["status"] == "completed",
    }
