from dataclasses import replace
from pathlib import Path
import sys

import streamlit as st
import streamlit.components.v1 as components

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from config import DEFAULT_CONFIG, TRAFFIC_SCENARIOS
from training.train import config_with_arrival_rates, train_q_learning, train_sarsa
from visualization.simulation_renderer import run_full_simulation, build_simulation_page
from visualization.video_renderer import generate_simulation_video
from visualization.visualization import plot_training_history


@st.cache_resource(show_spinner=False)
def get_trained_agent(algorithm: str, scenario: str, lane_count: int, free_left_turn: bool):
    config = build_config(scenario, lane_count, free_left_turn)
    if algorithm == "Q-Learning":
        return train_q_learning(config)
    return train_sarsa(config)


@st.cache_data(show_spinner=False)
def get_simulation_video(scenario: str, algorithm: str, lane_count: int, free_left_turn: bool):
    config = build_config(scenario, lane_count, free_left_turn)
    agent = None
    if algorithm in ("Q-Learning", "SARSA"):
        agent, _ = get_trained_agent(algorithm, scenario, lane_count, free_left_turn)
    return generate_simulation_video(config, agent, algorithm, fps=30)


def build_config(scenario: str, lane_count: int, free_left_turn: bool):
    config = config_with_arrival_rates(DEFAULT_CONFIG, TRAFFIC_SCENARIOS[scenario])
    simulation = replace(
        config.simulation,
        lane_count=lane_count,
        free_left_turn=free_left_turn,
    )
    return replace(config, simulation=simulation)


# Streamlit Page Setup
st.set_page_config(page_title="Adaptive Traffic RL", layout="wide", page_icon="🚦")
st.title("🚦 Adaptive Traffic Signal Control (RL Agent)")

# Sidebar Controls
with st.sidebar:
    st.header("Simulation Settings")
    scenario = st.selectbox("Traffic scenario", list(TRAFFIC_SCENARIOS), index=4)
    algorithm = st.selectbox("Algorithm", ["Fixed Time", "Q-Learning", "SARSA"], index=1)
    lane_count = st.selectbox(
        "Lane configuration", [2, 4], index=1, format_func=lambda lanes: f"{lanes} lanes"
    )
    free_left_turn = st.toggle("Free left turn", value=True)
    st.markdown("---")
    st.markdown("**Powered by:**\n- Gymnasium RL Environment\n- Imageio + FFmpeg\n- HTML5 Canvas Renderer")

config = build_config(scenario, lane_count, free_left_turn)

agent = None
history = None
if algorithm in ("Q-Learning", "SARSA"):
    with st.spinner(f"Training {algorithm} agent for {scenario}..."):
        agent, history = get_trained_agent(algorithm, scenario, lane_count, free_left_turn)

# Main Navigation Tabs
tab_canvas, tab_video, tab_metrics = st.tabs(["🎮 Interactive Canvas", "🎬 HD Video (Imageio + FFmpeg)", "📊 Training Metrics"])

with tab_canvas:
    st.subheader("Interactive 60FPS Canvas Animation")
    with st.spinner("Preparing interactive canvas simulation..."):
        steps = run_full_simulation(config, agent, algorithm)
        html_page = build_simulation_page(steps, lane_count, algorithm)
    components.html(html_page, height=960)

with tab_video:
    st.subheader("High-Definition MP4 Video (Imageio + FFmpeg)")
    st.caption("Pre-rendered frame-by-frame 60fps MP4 video generated using Imageio, FFmpeg, and Gymnasium API.")
    with st.spinner("Encoding MP4 video with Imageio and FFmpeg..."):
        video_path = get_simulation_video(scenario, algorithm, lane_count, free_left_turn)
    st.video(video_path)

with tab_metrics:
    st.subheader("Reinforcement Learning Training Performance")
    if history:
        col1, col2 = st.columns(2)
        col1.pyplot(plot_training_history(history, "reward"))
        col2.pyplot(plot_training_history(history, "average_waiting_time"))
    else:
        st.info("Fixed Time baseline controller does not have training metrics history.")
