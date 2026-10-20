from dataclasses import dataclass
from enum import Enum
from random import Random

from config import ProjectConfig, DEFAULT_CONFIG
from environment.signal_controller import Action, SignalController, SignalPhase


DIRECTIONS = ("north", "south", "east", "west")


class Movement(Enum):
    LEFT = "left"
    STRAIGHT = "straight"
    RIGHT = "right"


@dataclass(frozen=True)
class Vehicle:
    arrival_time: int
    direction: str = "north"
    movement: Movement = Movement.STRAIGHT
    lane_index: int = 0
    vehicle_id: int = 0


@dataclass
class StepResult:
    state: tuple[int, ...]
    reward: float
    done: bool
    info: dict[str, float | int | str]


class TrafficEnvironment:
    def __init__(self, config: ProjectConfig = DEFAULT_CONFIG):
        self.config = config
        self.signal = SignalController(config.signal)
        self.random = Random(config.simulation.random_seed)
        self.queues: dict[str, list[Vehicle]] = {direction: [] for direction in DIRECTIONS}
        self.time = 0
        self.throughput = 0
        self.completed_waiting_times: list[int] = []
        self.completed_travel_times: list[int] = []
        self.queue_history: list[int] = []
        self.reward_history: list[float] = []
        self.stop_count = 0
        self.last_departures = 0
        self.last_switched = False
        self.last_departed_vehicles: list[Vehicle] = []
        self.next_vehicle_id = 1
        self.unserved_duration: dict[str, int] = {direction: 0 for direction in DIRECTIONS}

    def reset(self, seed: int | None = None) -> tuple[int, ...]:
        self.random = Random(self.config.simulation.random_seed if seed is None else seed)
        self.signal.reset()
        self.queues = {direction: [] for direction in DIRECTIONS}
        self.time = 0
        self.throughput = 0
        self.completed_waiting_times = []
        self.completed_travel_times = []
        self.queue_history = []
        self.reward_history = []
        self.stop_count = 0
        self.last_departures = 0
        self.last_switched = False
        self.last_departed_vehicles = []
        self.next_vehicle_id = 1
        self.unserved_duration = {direction: 0 for direction in DIRECTIONS}
        return self.get_state()

    def step(self, action: Action) -> StepResult:
        self._add_arrivals()
        demand_directions = tuple(direction for direction in DIRECTIONS if self.queues[direction])
        for direction in DIRECTIONS:
            self.unserved_duration[direction] = (
                self.unserved_duration[direction] + 1 if self.queues[direction] else 0
            )
        requested_direction = self._priority_direction(demand_directions)
        starvation_phase = self._starvation_phase()
        self.last_switched = self.signal.update(
            action,
            starvation_phase,
            requested_direction,
            demand_directions,
        )
        self.last_departures = self._move_vehicles()

        total_queue = self.total_queue_length()
        self.queue_history.append(total_queue)
        self.stop_count += total_queue

        reward = self.calculate_reward()
        self.reward_history.append(reward)
        self.time += self.config.simulation.time_step_seconds
        done = self.time >= self.config.simulation.duration_seconds
        return StepResult(self.get_state(), reward, done, self.metrics())

    def get_state(self) -> tuple[int, ...]:
        queue_bins = [self._queue_bin(len(self.queues[direction])) for direction in DIRECTIONS]
        wait_bins = [self._wait_bin(self.oldest_waiting_time(direction)) for direction in DIRECTIONS]
        phase_value = self.signal.current_phase.value
        green_bin = min(self.signal.elapsed_green_time // 5, 6)
        return tuple(queue_bins + wait_bins + [phase_value, green_bin])

    def oldest_waiting_time(self, direction: str) -> int:
        if not self.queues[direction]:
            return 0
        return max(0, self.time - self.queues[direction][0].arrival_time)

    def total_queue_length(self) -> int:
        return sum(len(queue) for queue in self.queues.values())

    def calculate_reward(self) -> float:
        total_waiting_time = sum(self.oldest_waiting_time(direction) for direction in DIRECTIONS)
        reward = -self.config.reward.queue_penalty_weight * self.total_queue_length()
        reward -= self.config.reward.waiting_penalty_weight * total_waiting_time
        reward += self.config.reward.throughput_reward_weight * self.last_departures
        if self.last_switched:
            reward -= self.config.reward.switching_penalty_weight
        return reward

    def metrics(self) -> dict[str, float | int | str]:
        average_queue = sum(self.queue_history) / len(self.queue_history) if self.queue_history else 0.0
        average_wait = (
            sum(self.completed_waiting_times) / len(self.completed_waiting_times)
            if self.completed_waiting_times
            else 0.0
        )
        average_travel = (
            sum(self.completed_travel_times) / len(self.completed_travel_times)
            if self.completed_travel_times
            else 0.0
        )
        exceeded_wait = sum(
            1 for wait in self.completed_waiting_times if wait > self.config.signal.maximum_waiting_time
        )
        return {
            "time": self.time,
            "phase": self.signal.current_phase.name,
            "average_waiting_time": average_wait,
            "maximum_waiting_time": max(self.completed_waiting_times, default=0),
            "average_queue_length": average_queue,
            "maximum_queue_length": max(self.queue_history, default=0),
            "throughput": self.throughput,
            "average_travel_time": average_travel,
            "number_of_stops": self.stop_count,
            "number_of_switches": self.signal.switches,
            "safety_violations": self.signal.safety_violations,
            "illegal_switch_attempts": self.signal.illegal_switch_attempts,
            "vehicles_exceeding_max_wait": exceeded_wait,
            "cumulative_reward": sum(self.reward_history),
        }

    def _add_arrivals(self) -> None:
        for direction, rate in self.config.simulation.arrival_rates.items():
            if self.random.random() < rate:
                movement = self._choose_movement()
                self.queues[direction].append(
                    Vehicle(
                        arrival_time=self.time,
                        direction=direction,
                        movement=movement,
                        lane_index=self._lane_for_movement(movement),
                        vehicle_id=self.next_vehicle_id,
                    )
                )
                self.next_vehicle_id += 1

    def _move_vehicles(self) -> int:
        departures = 0
        self.last_departed_vehicles = []
        for direction in self.signal.green_directions():
            for _ in range(self.config.simulation.vehicles_per_green_step):
                if self.queues[direction]:
                    vehicle = self.queues[direction].pop(0)
                    self._record_departure(vehicle)
                    departures += 1
        if self.config.simulation.free_left_turn and departures == 0:
            candidates = [
                (self.oldest_waiting_time(direction), direction)
                for direction in DIRECTIONS
                if direction not in self.signal.green_directions()
                and self._free_left_vehicle_index(direction) is not None
            ]
            if candidates:
                _, direction = max(candidates)
                left_vehicle_index = self._free_left_vehicle_index(direction)
                vehicle = self.queues[direction].pop(left_vehicle_index)
                self._record_departure(vehicle)
                departures += 1
        self.throughput += departures
        return departures

    def _choose_movement(self) -> Movement:
        draw = self.random.random()
        left_probability = self.config.simulation.turn_probabilities["left"]
        straight_probability = self.config.simulation.turn_probabilities["straight"]
        if draw < left_probability:
            return Movement.LEFT
        if draw < left_probability + straight_probability:
            return Movement.STRAIGHT
        return Movement.RIGHT

    def _lane_for_movement(self, movement: Movement) -> int:
        if self.config.simulation.lane_count == 4 and movement == Movement.LEFT:
            return 0
        if self.config.simulation.lane_count == 4:
            return 1
        return 0

    def _record_departure(self, vehicle: Vehicle) -> None:
        waiting_time = max(0, self.time - vehicle.arrival_time)
        self.completed_waiting_times.append(waiting_time)
        self.completed_travel_times.append(waiting_time + self.config.simulation.time_step_seconds)
        self.last_departed_vehicles.append(vehicle)

    def _free_left_vehicle_index(self, direction: str) -> int | None:
        if self.config.simulation.lane_count == 2:
            if self.queues[direction] and self.queues[direction][0].movement == Movement.LEFT:
                return 0
            return None

        for index, vehicle in enumerate(self.queues[direction]):
            if vehicle.movement == Movement.LEFT and vehicle.lane_index == 0:
                return index
        return None

    def _starvation_phase(self) -> SignalPhase | None:
        threshold = self.config.signal.maximum_waiting_time
        urgent_direction = max(DIRECTIONS, key=self.oldest_waiting_time)
        if self.oldest_waiting_time(urgent_direction) >= threshold:
            return SignalPhase.NORTH_GREEN if urgent_direction == "north" else SignalPhase.SOUTH_GREEN if urgent_direction == "south" else SignalPhase.EAST_GREEN if urgent_direction == "east" else SignalPhase.WEST_GREEN
        return None

    def _priority_direction(self, demand_directions: tuple[str, ...]) -> str | None:
        if not demand_directions:
            return None

        def score(direction: str) -> tuple[float, int]:
            queue_length = len(self.queues[direction])
            oldest_wait = self.oldest_waiting_time(direction)
            return (
                4.0 * queue_length + oldest_wait + self.unserved_duration[direction],
                -DIRECTIONS.index(direction),
            )

        return max(demand_directions, key=score)

    def _queue_bin(self, queue_length: int) -> int:
        return min(queue_length // 3, 5)

    def _wait_bin(self, waiting_time: int) -> int:
        return min(waiting_time // 15, 6)
