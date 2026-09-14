import time
from dataclasses import replace

from agents.q_learning import QLearningAgent
from agents.sarsa import SarsaAgent
from config import ProjectConfig
from environment.traffic_environment import TrafficEnvironment


def train_q_learning(config: ProjectConfig, seed: int = 42) -> tuple[QLearningAgent, list[dict[str, float | int]]]:
    agent = QLearningAgent(config.learning, seed)
    history = []
    started_at = time.perf_counter()
    for episode in range(config.learning.episodes):
        environment = TrafficEnvironment(config)
        state = environment.reset(seed + episode)
        done = False
        while not done:
            action = agent.choose_action(state)
            result = environment.step(action)
            agent.update(state, action, result.reward, result.state, result.done)
            state = result.state
            done = result.done
        agent.decay_epsilon()
        metrics = environment.metrics()
        history.append(_episode_row(episode, metrics, agent.epsilon))
    history[-1]["training_time_seconds"] = time.perf_counter() - started_at
    return agent, history


def train_sarsa(config: ProjectConfig, seed: int = 42) -> tuple[SarsaAgent, list[dict[str, float | int]]]:
    agent = SarsaAgent(config.learning, seed)
    history = []
    started_at = time.perf_counter()
    for episode in range(config.learning.episodes):
        environment = TrafficEnvironment(config)
        state = environment.reset(seed + episode)
        action = agent.choose_action(state)
        done = False
        while not done:
            result = environment.step(action)
            next_action = agent.choose_action(result.state)
            agent.update(state, action, result.reward, result.state, next_action, result.done)
            state = result.state
            action = next_action
            done = result.done
        agent.decay_epsilon()
        metrics = environment.metrics()
        history.append(_episode_row(episode, metrics, agent.epsilon))
    history[-1]["training_time_seconds"] = time.perf_counter() - started_at
    return agent, history


def config_with_arrival_rates(config: ProjectConfig, arrival_rates: dict[str, float]) -> ProjectConfig:
    simulation = replace(config.simulation, arrival_rates=arrival_rates)
    return replace(config, simulation=simulation)


def _episode_row(
    episode: int, metrics: dict[str, float | int | str], epsilon: float
) -> dict[str, float | int]:
    return {
        "episode": episode,
        "reward": float(metrics["cumulative_reward"]),
        "average_waiting_time": float(metrics["average_waiting_time"]),
        "average_queue_length": float(metrics["average_queue_length"]),
        "throughput": int(metrics["throughput"]),
        "epsilon": epsilon,
    }
