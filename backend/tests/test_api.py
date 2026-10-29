import hashlib
import time
from dataclasses import replace
from pathlib import Path

from fastapi.testclient import TestClient

from backend.app.main import app
from baseline import FixedTimeController
from config import DEFAULT_CONFIG
from environment.traffic_environment import TrafficEnvironment
from training.train import train_q_learning

ROOT = Path(__file__).resolve().parents[2]
RESULTS = ROOT / "results" / "experiment_results.csv"


def _client():
    return TestClient(app)


def test_health():
    with _client() as client:
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


def test_configure_rejects_unknown_scenario():
    with _client() as client:
        response = client.post("/api/simulation/configure", json={"scenario": "rush-hour"})
        assert response.status_code == 422


def test_fixed_time_step_matches_environment():
    with _client() as client:
        configured = client.post(
            "/api/simulation/configure",
            json={"algorithm": "Fixed Time", "scenario": "medium", "duration_seconds": 12, "seed": 42, "speed": 1},
        )
        assert configured.status_code == 200
        client.post("/api/simulation/reset")
        response = client.post("/api/simulation/step")
        assert response.status_code == 200
        body = response.json()
        assert body["metrics"]["time"] == 1
        assert body["signal"]["phase"]
        assert body["phase_log"][-1]["phase"] == body["signal"]["phase"]
        assert body["phase_log"][-1]["step_index"] == 1

        simulation = replace(DEFAULT_CONFIG.simulation, duration_seconds=12, arrival_rates={"north": 0.10, "south": 0.10, "east": 0.10, "west": 0.10}, random_seed=42)
        config = replace(DEFAULT_CONFIG, simulation=simulation)
        environment = TrafficEnvironment(config)
        environment.reset(42)
        controller = FixedTimeController(config.signal.maximum_green_time)
        environment.step(controller.choose_action(environment))
        assert body["metrics"]["throughput"] == environment.metrics()["throughput"]
        assert body["metrics"]["cumulative_reward"] == environment.metrics()["cumulative_reward"]
        assert body["vehicles_in_network"] == environment.total_queue_length()


def test_arrival_scale_raises_live_demand_only():
    from backend.app.services.config_factory import build_config

    plain = build_config(scenario="medium", lane_count=2, free_left_turn=True, duration_seconds=12, seed=42)
    busy = build_config(
        scenario="medium",
        lane_count=2,
        free_left_turn=True,
        duration_seconds=12,
        seed=42,
        arrival_scale=4,
    )
    assert plain.simulation.arrival_rates["north"] == 0.10
    assert busy.simulation.arrival_rates["north"] == 0.40
    assert busy.simulation.vehicles_per_green_step == plain.simulation.vehicles_per_green_step
    with _client() as client:
        rejected = client.post("/api/simulation/configure", json={"arrival_scale": 8})
        assert rejected.status_code == 422
        configured = client.post(
            "/api/simulation/configure",
            json={"algorithm": "Fixed Time", "scenario": "medium", "duration_seconds": 20, "seed": 1, "arrival_scale": 4},
        )
        assert configured.status_code == 200
        assert configured.json()["arrival_scale"] == 4


def test_start_pause_does_not_keep_stepping():
    with _client() as client:
        client.post("/api/simulation/configure", json={"algorithm": "Fixed Time", "duration_seconds": 30, "seed": 7, "speed": 4})
        started = client.post("/api/simulation/start")
        assert started.status_code == 200
        assert started.json()["status"] == "running"
        again = client.post("/api/simulation/start")
        assert again.json()["status"] == "running"
        deadline = time.time() + 3
        while time.time() < deadline:
            if client.get("/api/simulation/state").json()["step_index"] >= 1:
                break
            time.sleep(0.05)
        paused = client.post("/api/simulation/pause")
        assert paused.status_code == 200
        step_index = paused.json()["step_index"]
        assert step_index >= 1
        time.sleep(0.3)
        later = client.get("/api/simulation/state")
        assert later.json()["status"] == "paused"
        assert later.json()["step_index"] == step_index


def test_q_learning_without_agent_is_rejected():
    with _client() as client:
        client.post("/api/simulation/configure", json={"algorithm": "Q-Learning", "scenario": "low", "duration_seconds": 10, "seed": 3})
        response = client.post("/api/simulation/start")
        assert response.status_code == 409
        assert "Train" in response.json()["detail"]


def test_training_job_matches_direct_function_and_can_control():
    with _client() as client:
        payload = {
            "algorithm": "Q-Learning",
            "scenario": "low",
            "duration_seconds": 15,
            "episodes": 2,
            "seed": 42,
            "lane_count": 2,
            "free_left_turn": True,
        }
        started = client.post("/api/training/start", json=payload)
        assert started.status_code == 202
        job_id = started.json()["id"]
        deadline = time.time() + 30
        status = started.json()
        while status["status"] in ("queued", "running") and time.time() < deadline:
            time.sleep(0.05)
            status = client.get(f"/api/training/status/{job_id}").json()
        assert status["status"] == "completed"
        assert status["history"]

        simulation = replace(
            DEFAULT_CONFIG.simulation,
            duration_seconds=15,
            arrival_rates={"north": 0.04, "south": 0.04, "east": 0.04, "west": 0.04},
            random_seed=42,
            lane_count=2,
            free_left_turn=True,
        )
        learning = replace(DEFAULT_CONFIG.learning, episodes=2)
        direct_agent, direct_history = train_q_learning(replace(DEFAULT_CONFIG, simulation=simulation, learning=learning), 42)
        assert [row["reward"] for row in status["history"]] == [row["reward"] for row in direct_history]
        assert [row["throughput"] for row in status["history"]] == [row["throughput"] for row in direct_history]

        client.post(
            "/api/simulation/configure",
            json={"algorithm": "Q-Learning", "scenario": "low", "duration_seconds": 15, "seed": 9, "agent_job_id": job_id},
        )
        running = client.post("/api/simulation/reset")
        assert running.status_code == 200
        assert running.json()["agent"]["job_id"] == job_id
        stepped = client.post("/api/simulation/step")
        assert stepped.json()["metrics"]["time"] == 1

        environment = TrafficEnvironment(replace(DEFAULT_CONFIG, simulation=replace(simulation, random_seed=9)))
        environment.reset(9)
        environment.step(direct_agent.choose_action(environment.get_state(), explore=False))
        assert stepped.json()["metrics"]["cumulative_reward"] == environment.metrics()["cumulative_reward"]


def test_cancel_queued_training_job(monkeypatch):
    monkeypatch.setattr("backend.app.services.training_service.TrainingService._spawn", lambda self, job_id: None)
    with _client() as client:
        first = client.post(
            "/api/training/start",
            json={"algorithm": "Q-Learning", "episodes": 1, "duration_seconds": 5, "scenario": "low"},
        )
        assert first.status_code == 202
        assert first.json()["status"] == "queued"
        cancelled = client.post(f"/api/training/cancel/{first.json()['id']}")
        assert cancelled.status_code == 200
        assert cancelled.json()["status"] == "cancelled"


def test_running_training_cannot_be_cancelled_or_duplicated(monkeypatch):
    gate = {"open": False}

    def blocked(config, seed=42):
        while not gate["open"]:
            time.sleep(0.01)
        from training.train import train_q_learning as real

        return real(config, seed)

    monkeypatch.setattr("backend.app.services.training_service.train_q_learning", blocked)
    with _client() as client:
        first = client.post(
            "/api/training/start",
            json={"algorithm": "Q-Learning", "episodes": 1, "duration_seconds": 5, "scenario": "low"},
        )
        assert first.status_code == 202
        deadline = time.time() + 3
        status = first.json()["status"]
        while status != "running" and time.time() < deadline:
            time.sleep(0.02)
            status = client.get(f"/api/training/status/{first.json()['id']}").json()["status"]
        assert status == "running"
        second = client.post(
            "/api/training/start",
            json={"algorithm": "SARSA", "episodes": 1, "duration_seconds": 5, "scenario": "low"},
        )
        assert second.status_code == 409
        cancel_running = client.post(f"/api/training/cancel/{first.json()['id']}")
        assert cancel_running.status_code == 409
        gate["open"] = True


def test_results_filters_export_and_do_not_rewrite_source():
    before = hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    with _client() as client:
        experiments = client.get("/api/experiments")
        assert experiments.status_code == 200
        assert any(item["id"] == "traffic_scenario" for item in experiments.json()["experiments"])
        detail = client.get("/api/experiments/traffic_scenario")
        assert detail.status_code == 200
        assert detail.json()["records"]
        missing = client.get("/api/experiments/does-not-exist")
        assert missing.status_code == 404
        summary = client.get("/api/results/summary", params={"experiment": "traffic_scenario", "scenario": "high"})
        assert summary.status_code == 200
        rows = summary.json()["records"]
        q_row = next(row for row in rows if row["controller"] == "Q-Learning")
        assert q_row["percent_difference_vs_fixed_time"]["average_waiting_time"] is not None
        exported = client.get("/api/results/export", params={"experiment": "maximum_wait", "scenario": "90", "controller": "SARSA"})
        assert exported.status_code == 200
        assert "SARSA" in exported.text
        assert exported.headers["content-type"].startswith("text/csv")
    after = hashlib.sha256(RESULTS.read_bytes()).hexdigest()
    assert before == after


def test_zero_baseline_percentage_is_null():
    from backend.app.services.results_service import _percent

    assert _percent(1, 0) is None
    assert _percent(0, 0) is None


def test_video_job_completes_for_a_short_fixed_time_clip():
    with _client() as client:
        started = client.post(
            "/api/video/generate",
            json={
                "algorithm": "Fixed Time",
                "scenario": "low",
                "duration_seconds": 4,
                "fps": 4,
                "frames_per_step": 1,
                "seed": 1,
            },
        )
        assert started.status_code == 202
        job_id = started.json()["id"]
        deadline = time.time() + 90
        status = started.json()
        while status["status"] in ("queued", "running") and time.time() < deadline:
            time.sleep(0.2)
            status = client.get(f"/api/video/status/{job_id}").json()
        assert status["status"] == "completed", status
        download = client.get(status["download_url"])
        assert download.status_code == 200
        assert download.headers["content-type"].startswith("video/mp4")
        assert download.content[:3] != b""
        missing = client.get("/api/video/not-a-real-job/file")
        assert missing.status_code == 404


def test_video_frame_limit():
    with _client() as client:
        response = client.post(
            "/api/video/generate",
            json={"algorithm": "Fixed Time", "duration_seconds": 300, "frames_per_step": 15, "fps": 10},
        )
        assert response.status_code == 422
        assert "frames" in response.json()["detail"]


def test_step_while_running_is_rejected():
    with _client() as client:
        client.post("/api/simulation/configure", json={"algorithm": "Fixed Time", "duration_seconds": 40, "speed": 1})
        client.post("/api/simulation/start")
        response = client.post("/api/simulation/step")
        assert response.status_code == 409
        client.post("/api/simulation/pause")
