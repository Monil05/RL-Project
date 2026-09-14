from dataclasses import replace
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from baseline import FixedTimeController
from config import DEFAULT_CONFIG, TRAFFIC_SCENARIOS
from environment.signal_controller import Action
from environment.traffic_environment import TrafficEnvironment
from training.train import config_with_arrival_rates, train_q_learning, train_sarsa
from visualization.live_simulation import (
    advance_active_movements,
    create_active_movements,
    render_live_intersection,
)
from visualization.visualization import plot_training_history


SPEEDS = {
    "Slow": {"progress": 0.14},
    "Normal": {"progress": 0.24},
    "Fast": {"progress": 0.40},
}


@st.cache_resource(show_spinner=False)
def get_trained_agent(algorithm: str, scenario: str, lane_count: int, free_left_turn: bool):
    config = build_config(scenario, lane_count, free_left_turn)
    if algorithm == "Q-Learning":
        return train_q_learning(config)
    return train_sarsa(config)


def build_config(scenario: str, lane_count: int, free_left_turn: bool):
    config = config_with_arrival_rates(DEFAULT_CONFIG, TRAFFIC_SCENARIOS[scenario])
    simulation = replace(
        config.simulation,
        lane_count=lane_count,
        free_left_turn=free_left_turn,
    )
    return replace(config, simulation=simulation)


def reset_simulation(config, algorithm: str) -> None:
    st.session_state.environment = TrafficEnvironment(config)
    st.session_state.environment.reset(config.simulation.random_seed)
    st.session_state.running = False
    st.session_state.done = False
    st.session_state.active_movements = []
    st.session_state.last_action = Action.KEEP
    st.session_state.fixed_controller = FixedTimeController(config.signal.maximum_green_time)
    st.session_state.signature = current_signature(algorithm, config)


def current_signature(algorithm: str, config) -> tuple[str, int, bool, tuple[tuple[str, float], ...]]:
    return (
        algorithm,
        config.simulation.lane_count,
        config.simulation.free_left_turn,
        tuple(sorted(config.simulation.arrival_rates.items())),
    )


def choose_action(algorithm: str, agent) -> Action:
    environment = st.session_state.environment
    if algorithm == "Fixed Time":
        return st.session_state.fixed_controller.choose_action(environment)
    return agent.choose_action(environment.get_state(), explore=False)


def advance_frame(algorithm: str, agent, progress_step: float) -> None:
    if st.session_state.active_movements:
        st.session_state.active_movements = advance_active_movements(
            st.session_state.active_movements, progress_step
        )
        return

    environment = st.session_state.environment
    action = choose_action(algorithm, agent)
    result = environment.step(action)
    st.session_state.last_action = action
    st.session_state.done = result.done
    st.session_state.active_movements = create_active_movements(environment.last_departed_vehicles)
    if result.done:
        st.session_state.running = False


st.set_page_config(page_title="Adaptive Traffic RL", layout="wide")
st.title("Adaptive Traffic Signal Control")

with st.sidebar:
    scenario = st.selectbox("Traffic scenario", list(TRAFFIC_SCENARIOS), index=4)
    algorithm = st.selectbox("Algorithm", ["Fixed Time", "Q-Learning", "SARSA"], index=1)
    lane_count = st.selectbox(
        "Lane configuration", [2, 4], index=1, format_func=lambda lanes: f"{lanes} lanes"
    )
    free_left_turn = st.toggle("Free left turn", value=True)
    speed = st.selectbox("Speed", list(SPEEDS), index=1)

config = build_config(scenario, lane_count, free_left_turn)
agent = None
history = None
if algorithm in ("Q-Learning", "SARSA"):
    with st.spinner(f"Training {algorithm} for this scenario..."):
        agent, history = get_trained_agent(algorithm, scenario, lane_count, free_left_turn)

if "environment" not in st.session_state:
    reset_simulation(config, algorithm)

if st.session_state.signature != current_signature(algorithm, config):
    reset_simulation(config, algorithm)

with st.sidebar:
    control_columns = st.columns(3)
    if control_columns[0].button("START", use_container_width=True):
        st.session_state.running = True
    if control_columns[1].button("STOP", use_container_width=True):
        st.session_state.running = False
    if control_columns[2].button("RESET", use_container_width=True):
        reset_simulation(config, algorithm)


@st.fragment(run_every=0.24)
def render_simulation() -> None:
    if st.session_state.running and not st.session_state.done:
        advance_frame(algorithm, agent, SPEEDS[speed]["progress"])

    environment = st.session_state.environment
    metrics = environment.metrics()
    components.html(
        render_live_intersection(
            environment,
            st.session_state.active_movements,
            lane_count,
            st.session_state.last_action,
            algorithm,
        ),
        height=700,
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric("Time", f"{metrics['time']}s")
    metric_columns[1].metric("Throughput", metrics["throughput"])
    metric_columns[2].metric("Average Wait", f"{metrics['average_waiting_time']:.2f}s")
    metric_columns[3].metric("Max Wait", f"{metrics['maximum_waiting_time']}s")
    metric_columns[4].metric("Reward", f"{metrics['cumulative_reward']:.1f}")

    if history:
        graph_columns = st.columns(2)
        graph_columns[0].pyplot(plot_training_history(history, "reward"))
        graph_columns[1].pyplot(plot_training_history(history, "average_waiting_time"))


render_simulation()
