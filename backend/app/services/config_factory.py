"""Build ProjectConfig values for the API without changing config defaults."""

from dataclasses import asdict, replace

from backend.app.bootstrap import ROOT  # noqa: F401  (imports after path setup)
from backend.app.services.errors import ApiError
from config import DEFAULT_CONFIG, TRAFFIC_SCENARIOS, ProjectConfig

ALGORITHMS = ("Fixed Time", "Q-Learning", "SARSA")
RL_ALGORITHMS = ("Q-Learning", "SARSA")


def require_algorithm(algorithm: str, allow_fixed: bool = True) -> str:
    allowed = ALGORITHMS if allow_fixed else RL_ALGORITHMS
    if algorithm not in allowed:
        raise ApiError(422, f"Algorithm must be one of: {', '.join(allowed)}.")
    return algorithm


def require_scenario(scenario: str) -> str:
    if scenario not in TRAFFIC_SCENARIOS:
        names = ", ".join(TRAFFIC_SCENARIOS)
        raise ApiError(422, f"Unknown traffic scenario '{scenario}'. Choose one of: {names}.")
    return scenario


def build_config(
    *,
    scenario: str,
    lane_count: int,
    free_left_turn: bool,
    duration_seconds: int,
    seed: int,
    episodes: int | None = None,
    learning_rate: float | None = None,
    discount_factor: float | None = None,
    epsilon: float | None = None,
    epsilon_decay: float | None = None,
    minimum_epsilon: float | None = None,
    arrival_scale: float = 1.0,
) -> ProjectConfig:
    require_scenario(scenario)
    if arrival_scale < 1 or arrival_scale > 6:
        raise ApiError(422, "Arrival scale must be between 1 and 6.")
    if lane_count not in (2, 4):
        raise ApiError(422, "Lane count must be 2 or 4.")
    if duration_seconds < 1 or duration_seconds > 3600:
        raise ApiError(422, "Duration must be between 1 and 3600 seconds.")
    if seed < 0 or seed > 2_147_483_647:
        raise ApiError(422, "Seed must be a non-negative 32-bit integer.")

    learning_values = {
        "episodes": episodes,
        "learning_rate": learning_rate,
        "discount_factor": discount_factor,
        "epsilon": epsilon,
        "epsilon_decay": epsilon_decay,
        "minimum_epsilon": minimum_epsilon,
    }
    _validate_learning(learning_values)
    learning = DEFAULT_CONFIG.learning
    overrides = {key: value for key, value in learning_values.items() if value is not None}
    if overrides:
        learning = replace(learning, **overrides)

    base_rates = dict(TRAFFIC_SCENARIOS[scenario])
    arrival_rates = (
        base_rates
        if arrival_scale == 1
        else {direction: min(0.85, rate * arrival_scale) for direction, rate in base_rates.items()}
    )
    simulation = replace(
        DEFAULT_CONFIG.simulation,
        arrival_rates=arrival_rates,
        lane_count=lane_count,
        free_left_turn=free_left_turn,
        duration_seconds=duration_seconds,
        random_seed=seed,
    )
    return replace(DEFAULT_CONFIG, simulation=simulation, learning=learning)


def _validate_learning(values: dict) -> None:
    ranges = {
        "episodes": (1, 1000),
        "learning_rate": (0.0, 1.0),
        "discount_factor": (0.0, 1.0),
        "epsilon": (0.0, 1.0),
        "epsilon_decay": (0.0, 1.0),
        "minimum_epsilon": (0.0, 1.0),
    }
    for key, (low, high) in ranges.items():
        value = values.get(key)
        if value is None:
            continue
        if value < low or value > high:
            raise ApiError(422, f"{key} must be between {low} and {high}.")
    epsilon = values.get("epsilon")
    minimum = values.get("minimum_epsilon")
    if epsilon is not None and minimum is not None and minimum > epsilon:
        raise ApiError(422, "minimum_epsilon cannot be greater than epsilon.")


def control_fingerprint(config: ProjectConfig) -> dict:
    """Environment identity used to decide whether a trained agent can control a session.

    Learning rates, episode count, duration, and seed are not part of this identity.
    They remain visible on the training job.
    """
    return {
        "arrival_rates": dict(config.simulation.arrival_rates),
        "lane_count": config.simulation.lane_count,
        "free_left_turn": config.simulation.free_left_turn,
        "turn_probabilities": dict(config.simulation.turn_probabilities),
        "vehicles_per_green_step": config.simulation.vehicles_per_green_step,
        "time_step_seconds": config.simulation.time_step_seconds,
        "signal": asdict(config.signal),
    }


def public_config(config: ProjectConfig) -> dict:
    return {
        "signal": asdict(config.signal),
        "reward": asdict(config.reward),
        "learning": asdict(config.learning),
        "simulation": {
            "duration_seconds": config.simulation.duration_seconds,
            "time_step_seconds": config.simulation.time_step_seconds,
            "vehicles_per_green_step": config.simulation.vehicles_per_green_step,
            "random_seed": config.simulation.random_seed,
            "lane_count": config.simulation.lane_count,
            "free_left_turn": config.simulation.free_left_turn,
            "turn_probabilities": dict(config.simulation.turn_probabilities),
            "arrival_rates": dict(config.simulation.arrival_rates),
        },
    }


def defaults_payload() -> dict:
    return {
        "algorithms": list(ALGORITHMS),
        "training_algorithms": list(RL_ALGORITHMS),
        "scenarios": {
            name: dict(rates) for name, rates in TRAFFIC_SCENARIOS.items()
        },
        "actions": ["KEEP", "SWITCH"],
        "config": public_config(DEFAULT_CONFIG),
        "notes": [
            "Training and evaluation call the existing Python functions. Hyperparameter fields left blank keep LearningConfig defaults.",
            "The existing trainers do not report episode progress until the function returns.",
            "Cancellation is only possible while a job is still queued.",
            "Existing experiment CSV files do not contain timestamps.",
        ],
    }
