"""Interactive session around TrafficEnvironment. One ticker thread owns automatic steps."""

from __future__ import annotations

import threading
import time
from backend.app.services.config_factory import build_config, control_fingerprint
from backend.app.services.errors import ApiError
from baseline import FixedTimeController
from config import ProjectConfig
from environment.traffic_environment import DIRECTIONS, TrafficEnvironment, Vehicle


class SimulationService:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._wake = threading.Event()
        self._shutdown = threading.Event()
        self._status = "idle"
        self._speed = 1.0
        self._algorithm = "Fixed Time"
        self._scenario = "medium"
        self._lane_count = 2
        self._free_left_turn = True
        self._duration_seconds = 300
        self._seed = 42
        self._arrival_scale = 1.0
        self._agent_job_id: str | None = None
        self._config: ProjectConfig | None = None
        self._env: TrafficEnvironment | None = None
        self._controller = None
        self._agent_meta: dict | None = None
        self._step_index = 0
        self._series: list[dict] = []
        self._departure_log: list[dict] = []
        self._phase_log: list[dict] = []
        self._dirty = True
        self._error: str | None = None
        self._agents = None
        self._thread = threading.Thread(target=self._loop, name="simulation-ticker", daemon=True)
        self._thread.start()

    def bind_agents(self, training_service) -> None:
        self._agents = training_service

    def shutdown(self) -> None:
        self._shutdown.set()
        self._wake.set()

    def configure(self, payload) -> dict:
        build_config(
            scenario=payload.scenario,
            lane_count=payload.lane_count,
            free_left_turn=payload.free_left_turn,
            duration_seconds=payload.duration_seconds,
            seed=payload.seed,
            arrival_scale=payload.arrival_scale,
        )
        with self._lock:
            structural_same = (
                payload.algorithm == self._algorithm
                and payload.scenario == self._scenario
                and payload.lane_count == self._lane_count
                and payload.free_left_turn == self._free_left_turn
                and payload.duration_seconds == self._duration_seconds
                and payload.seed == self._seed
                and payload.arrival_scale == self._arrival_scale
                and payload.agent_job_id == self._agent_job_id
            )
            if not structural_same and self._status in ("running", "paused"):
                raise ApiError(
                    409,
                    "Pause is not enough to change the controller or demand. Reset the simulation first.",
                )
            self._speed = payload.speed
            if structural_same:
                return self._snapshot_unlocked()
            self._algorithm = payload.algorithm
            self._scenario = payload.scenario
            self._lane_count = payload.lane_count
            self._free_left_turn = payload.free_left_turn
            self._duration_seconds = payload.duration_seconds
            self._seed = payload.seed
            self._arrival_scale = payload.arrival_scale
            self._agent_job_id = payload.agent_job_id
            self._dirty = True
            self._error = None
            if self._status == "completed":
                self._status = "idle"
            return self._snapshot_unlocked()

    def start(self) -> dict:
        with self._lock:
            if self._status == "running":
                return self._snapshot_unlocked()
            if self._status == "paused" and not self._dirty and self._env is not None:
                self._status = "running"
                self._error = None
                self._wake.set()
                return self._snapshot_unlocked()
            self._build_unlocked()
            self._status = "running"
            self._error = None
            self._wake.set()
            return self._snapshot_unlocked()

    def pause(self) -> dict:
        with self._lock:
            if self._status != "running":
                raise ApiError(409, "Simulation is not running.")
            self._status = "paused"
            return self._snapshot_unlocked()

    def reset(self) -> dict:
        with self._lock:
            self._build_unlocked()
            self._status = "idle"
            self._error = None
            return self._snapshot_unlocked()

    def step(self) -> dict:
        with self._lock:
            if self._status == "running":
                raise ApiError(409, "Automatic playback is running. Pause it before single-stepping.")
            if self._env is None or self._dirty:
                self._build_unlocked()
                self._status = "paused"
            if self._env.time >= self._env.config.simulation.duration_seconds:
                self._status = "completed"
                return self._snapshot_unlocked()
            self._advance_unlocked()
            if self._env.time >= self._env.config.simulation.duration_seconds:
                self._status = "completed"
            return self._snapshot_unlocked()

    def snapshot(self) -> dict:
        with self._lock:
            return self._snapshot_unlocked()

    def _build_unlocked(self) -> None:
        config = build_config(
            scenario=self._scenario,
            lane_count=self._lane_count,
            free_left_turn=self._free_left_turn,
            duration_seconds=self._duration_seconds,
            seed=self._seed,
            arrival_scale=self._arrival_scale,
        )
        controller, meta = self._resolve_controller(config)
        environment = TrafficEnvironment(config)
        environment.reset(self._seed)
        self._config = config
        self._env = environment
        self._controller = controller
        self._agent_meta = meta
        self._step_index = 0
        self._series = []
        self._departure_log = []
        self._phase_log = [_phase_entry(environment, 0)]
        self._dirty = False

    def _resolve_controller(self, config: ProjectConfig):
        if self._algorithm == "Fixed Time":
            return FixedTimeController(config.signal.maximum_green_time), None
        if self._agents is None:
            raise ApiError(409, "Training storage is not available.")
        record = self._agents.resolve_agent(
            self._algorithm,
            control_fingerprint(config),
            self._agent_job_id,
        )
        return record["agent"], record["meta"]

    def _advance_unlocked(self) -> None:
        environment = self._env
        assert environment is not None
        if self._algorithm == "Fixed Time":
            action = self._controller.choose_action(environment)
        else:
            action = self._controller.choose_action(environment.get_state(), explore=False)
        environment.step(action)
        self._step_index += 1
        metrics = _metrics(environment)
        self._series.append(
            {
                "time": metrics["time"],
                "average_waiting_time": metrics["average_waiting_time"],
                "average_queue_length": metrics["average_queue_length"],
                "throughput": metrics["throughput"],
                "cumulative_reward": metrics["cumulative_reward"],
                "number_of_switches": metrics["number_of_switches"],
            }
        )
        departed = [_vehicle(vehicle) for vehicle in environment.last_departed_vehicles]
        self._departure_log.append({"step_index": self._step_index, "departed": departed})
        self._departure_log = self._departure_log[-40:]
        self._phase_log.append(_phase_entry(environment, self._step_index))
        self._phase_log = self._phase_log[-40:]

    def _snapshot_unlocked(self) -> dict:
        environment = self._env
        metrics = _metrics(environment) if environment is not None and not self._dirty else None
        queues = {direction: [] for direction in DIRECTIONS}
        departed: list[dict] = []
        signal = None
        if environment is not None and not self._dirty:
            queues = {
                direction: [_vehicle(vehicle) for vehicle in environment.queues[direction]]
                for direction in DIRECTIONS
            }
            departed = [_vehicle(vehicle) for vehicle in environment.last_departed_vehicles]
            signal = {
                "phase": environment.signal.current_phase.name,
                "active_direction": environment.signal.active_direction,
                "elapsed_green_time": environment.signal.elapsed_green_time,
                "green_directions": list(environment.signal.green_directions()),
                "switches": environment.signal.switches,
                "illegal_switch_attempts": environment.signal.illegal_switch_attempts,
                "safety_violations": environment.signal.safety_violations,
            }
        vehicles = sum(len(queue) for queue in queues.values())
        return {
            "ready": environment is not None and not self._dirty,
            "status": self._status,
            "algorithm": self._algorithm,
            "scenario": self._scenario,
            "lane_count": self._lane_count,
            "free_left_turn": self._free_left_turn,
            "duration_seconds": self._duration_seconds,
            "seed": self._seed,
            "speed": self._speed,
            "arrival_scale": self._arrival_scale,
            "step_index": self._step_index,
            "vehicles_in_network": vehicles if metrics is not None else None,
            "signal": signal,
            "queues": queues,
            "queue_lengths": {direction: len(queues[direction]) for direction in DIRECTIONS},
            "departed": departed,
            "departure_log": list(self._departure_log),
            "phase_log": list(self._phase_log),
            "metrics": metrics,
            "series": list(self._series),
            "agent": self._agent_meta,
            "error": self._error,
            "message": None
            if metrics is not None
            else "No simulation is loaded. Choose a configuration and press Start or Reset.",
        }

    def _loop(self) -> None:
        next_step_at = time.perf_counter()
        while not self._shutdown.is_set():
            with self._lock:
                running = (
                    self._status == "running"
                    and self._env is not None
                    and not self._dirty
                    and self._env.time < self._env.config.simulation.duration_seconds
                )
                speed = self._speed
                if self._status == "running" and self._env is not None and self._env.time >= self._env.config.simulation.duration_seconds:
                    self._status = "completed"
                    running = False
            if not running:
                self._wake.wait(0.2)
                self._wake.clear()
                next_step_at = time.perf_counter()
                continue
            now = time.perf_counter()
            if now < next_step_at:
                time.sleep(min(0.05, next_step_at - now))
                continue
            with self._lock:
                if (
                    self._status == "running"
                    and self._env is not None
                    and self._env.time < self._env.config.simulation.duration_seconds
                ):
                    self._advance_unlocked()
                    if self._env.time >= self._env.config.simulation.duration_seconds:
                        self._status = "completed"
            next_step_at = time.perf_counter() + max(0.05, 0.25 / max(speed, 0.25))


def _phase_entry(environment: TrafficEnvironment, step_index: int) -> dict:
    return {
        "step_index": step_index,
        "phase": environment.signal.current_phase.name,
        "active_direction": environment.signal.active_direction,
    }


def _vehicle(vehicle: Vehicle) -> dict:
    return {
        "id": vehicle.vehicle_id,
        "direction": vehicle.direction,
        "movement": vehicle.movement.value,
        "lane_index": vehicle.lane_index,
        "arrival_time": vehicle.arrival_time,
    }


def _metrics(environment: TrafficEnvironment) -> dict:
    raw = environment.metrics()
    numeric_ints = {
        "time",
        "maximum_waiting_time",
        "maximum_queue_length",
        "throughput",
        "number_of_stops",
        "number_of_switches",
        "safety_violations",
        "illegal_switch_attempts",
        "vehicles_exceeding_max_wait",
    }
    payload = {}
    for key, value in raw.items():
        if key == "phase":
            payload[key] = str(value)
        elif key in numeric_ints:
            payload[key] = int(value)
        else:
            payload[key] = float(value)
    if environment.reward_history:
        payload["last_reward"] = float(environment.reward_history[-1])
    else:
        payload["last_reward"] = None
    return payload

