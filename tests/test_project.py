from dataclasses import replace

from agents.q_learning import QLearningAgent
from agents.sarsa import SarsaAgent
from baseline import run_fixed_time
from config import DEFAULT_CONFIG
from environment.signal_controller import Action, SignalPhase
from environment.traffic_environment import Movement, TrafficEnvironment, Vehicle
from evaluation.evaluate import evaluate_agent
from training.train import train_q_learning, train_sarsa
from visualization.live_simulation import create_active_movements, render_live_intersection


def short_config():
    simulation = replace(DEFAULT_CONFIG.simulation, duration_seconds=40)
    learning = replace(DEFAULT_CONFIG.learning, episodes=3)
    return replace(DEFAULT_CONFIG, simulation=simulation, learning=learning)


def test_vehicle_arrival_and_departure():
    config = replace(
        short_config().simulation,
        arrival_rates={"north": 1.0, "south": 0.0, "east": 0.0, "west": 0.0},
    )
    project_config = replace(short_config(), simulation=config)
    environment = TrafficEnvironment(project_config)
    environment.reset(1)
    result = environment.step(Action.KEEP)
    assert result.info["throughput"] >= 1


def test_minimum_green_blocks_early_switch():
    environment = TrafficEnvironment(short_config())
    environment.reset(1)
    environment.queues["north"].append(Vehicle(arrival_time=0, direction="north"))
    environment.step(Action.SWITCH)
    assert environment.signal.current_phase == SignalPhase.NORTH_GREEN
    assert environment.signal.safety_violations == 0
    assert environment.signal.illegal_switch_attempts == 0


def test_switch_sequence_after_minimum_green():
    environment = TrafficEnvironment(short_config())
    environment.reset(1)
    environment.queues["north"] = [Vehicle(arrival_time=0, direction="north", vehicle_id=index) for index in range(20)]
    environment.queues["east"] = [Vehicle(arrival_time=0, direction="east", vehicle_id=100 + index) for index in range(20)]
    for _ in range(environment.config.signal.minimum_green_time + 1):
        environment.step(Action.KEEP)
    environment.step(Action.SWITCH)
    assert environment.signal.current_phase == SignalPhase.YELLOW
    for _ in range(environment.config.signal.yellow_interval):
        environment.step(Action.KEEP)
    assert environment.signal.current_phase == SignalPhase.ALL_RED
    environment.step(Action.KEEP)
    assert environment.signal.current_phase in (
        SignalPhase.NORTH_GREEN,
        SignalPhase.SOUTH_GREEN,
        SignalPhase.EAST_GREEN,
        SignalPhase.WEST_GREEN,
    )
    assert len(environment.signal.green_directions()) == 1


def test_starvation_forces_service():
    environment = TrafficEnvironment(short_config())
    environment.reset(1)
    environment.queues["north"].append(Vehicle(arrival_time=0, direction="north"))
    environment.queues["west"].append(Vehicle(arrival_time=-100))
    environment.signal.active_direction = "north"
    environment.signal.current_phase = SignalPhase.NORTH_GREEN
    environment.signal.elapsed_green_time = environment.config.signal.minimum_green_time
    environment.step(Action.KEEP)
    assert environment.signal.current_phase == SignalPhase.YELLOW


def test_training_and_evaluation_pipeline():
    config = short_config()
    q_agent, q_history = train_q_learning(config)
    sarsa_agent, sarsa_history = train_sarsa(config)
    assert isinstance(q_agent, QLearningAgent)
    assert isinstance(sarsa_agent, SarsaAgent)
    assert len(q_history) == config.learning.episodes
    assert len(sarsa_history) == config.learning.episodes
    assert evaluate_agent(q_agent, config)["throughput"] >= 0
    assert run_fixed_time(config)["safety_violations"] == 0


def test_four_lane_left_turn_uses_dedicated_incoming_lane():
    config = short_config()
    simulation = replace(
        config.simulation,
        lane_count=4,
        turn_probabilities={"left": 1.0, "straight": 0.0, "right": 0.0},
        arrival_rates={"north": 1.0, "south": 0.0, "east": 0.0, "west": 0.0},
    )
    environment = TrafficEnvironment(replace(config, simulation=simulation))
    environment.reset(1)
    environment.step(Action.KEEP)
    assert all(vehicle.lane_index == 0 for vehicle in environment.last_departed_vehicles)


def test_two_lane_configuration_has_single_incoming_lane():
    config = short_config()
    simulation = replace(
        config.simulation,
        lane_count=2,
        free_left_turn=False,
        turn_probabilities={"left": 1.0, "straight": 0.0, "right": 0.0},
        arrival_rates={"north": 0.0, "south": 0.0, "east": 1.0, "west": 0.0},
    )
    environment = TrafficEnvironment(replace(config, simulation=simulation))
    environment.reset(1)
    environment.step(Action.KEEP)
    assert environment.last_departed_vehicles[0].lane_index == 0


def test_free_left_turn_allows_red_phase_left_departure():
    config = short_config()
    simulation = replace(config.simulation, free_left_turn=True)
    environment = TrafficEnvironment(replace(config, simulation=simulation))
    environment.reset(1)
    environment.queues["east"].append(
        Vehicle(arrival_time=0, direction="east", movement=Movement.LEFT, lane_index=0, vehicle_id=1)
    )
    environment.step(Action.KEEP)
    assert environment.last_departed_vehicles[0].movement == Movement.LEFT


def test_free_left_does_not_skip_blocking_vehicle_in_two_lane_queue():
    config = short_config()
    simulation = replace(config.simulation, lane_count=2, free_left_turn=True)
    environment = TrafficEnvironment(replace(config, simulation=simulation))
    environment.reset(1)
    environment.queues["east"].append(
        Vehicle(arrival_time=0, direction="east", movement=Movement.STRAIGHT, lane_index=0, vehicle_id=1)
    )
    environment.queues["east"].append(
        Vehicle(arrival_time=0, direction="east", movement=Movement.LEFT, lane_index=0, vehicle_id=2)
    )
    environment.step(Action.KEEP)
    assert environment.throughput == 1
    assert environment.last_departed_vehicles[0].movement == Movement.STRAIGHT
    assert len(environment.queues["east"]) == 1


def test_live_svg_contains_lights_and_vehicle_routes():
    environment = TrafficEnvironment(short_config())
    environment.reset(1)
    vehicle = Vehicle(arrival_time=0, direction="north", movement=Movement.RIGHT, lane_index=0, vehicle_id=1)
    active_movements = create_active_movements([vehicle])
    svg = render_live_intersection(environment, active_movements, 4, Action.KEEP, "Q-Learning")
    assert "<svg" in svg
    assert "Q-Learning" not in svg
    assert "Phase:" not in svg
    assert "<image" in svg
    assert "data-start-angle" in svg
    assert "requestAnimationFrame" in svg
