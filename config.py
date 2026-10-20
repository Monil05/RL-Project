from dataclasses import dataclass, field


@dataclass(frozen=True)
class SignalConfig:
    minimum_green_time: int = 10
    maximum_green_time: int = 30
    yellow_interval: int = 3
    all_red_clearance: int = 1
    maximum_waiting_time: int = 90


@dataclass(frozen=True)
class RewardConfig:
    queue_penalty_weight: float = 1.0
    waiting_penalty_weight: float = 0.1
    throughput_reward_weight: float = 2.0
    switching_penalty_weight: float = 0.5


@dataclass(frozen=True)
class LearningConfig:
    learning_rate: float = 0.1
    discount_factor: float = 0.95
    epsilon: float = 1.0
    epsilon_decay: float = 0.995
    minimum_epsilon: float = 0.05
    episodes: int = 120


@dataclass(frozen=True)
class SimulationConfig:
    duration_seconds: int = 300
    time_step_seconds: int = 1
    vehicles_per_green_step: int = 1
    random_seed: int = 42
    lane_count: int = 2
    free_left_turn: bool = True
    turn_probabilities: dict[str, float] = field(
        default_factory=lambda: {
            "left": 0.25,
            "straight": 0.50,
            "right": 0.25,
        }
    )
    arrival_rates: dict[str, float] = field(
        default_factory=lambda: {
            "north": 0.10,
            "south": 0.10,
            "east": 0.10,
            "west": 0.10,
        }
    )


TRAFFIC_SCENARIOS: dict[str, dict[str, float]] = {
    "low": {"north": 0.04, "south": 0.04, "east": 0.04, "west": 0.04},
    "medium": {"north": 0.10, "south": 0.10, "east": 0.10, "west": 0.10},
    "high": {"north": 0.18, "south": 0.18, "east": 0.18, "west": 0.18},
    "balanced": {"north": 0.12, "south": 0.12, "east": 0.12, "west": 0.12},
    "asymmetric": {"north": 0.20, "south": 0.18, "east": 0.05, "west": 0.04},
    "unseen": {"north": 0.07, "south": 0.16, "east": 0.11, "west": 0.03},
}


@dataclass(frozen=True)
class ProjectConfig:
    signal: SignalConfig = field(default_factory=SignalConfig)
    reward: RewardConfig = field(default_factory=RewardConfig)
    learning: LearningConfig = field(default_factory=LearningConfig)
    simulation: SimulationConfig = field(default_factory=SimulationConfig)


DEFAULT_CONFIG = ProjectConfig()
