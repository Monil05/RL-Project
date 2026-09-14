import time

from agents.tabular_agent import TabularAgent
from baseline import run_fixed_time
from config import ProjectConfig
from environment.traffic_environment import TrafficEnvironment


def evaluate_agent(
    agent: TabularAgent, config: ProjectConfig, seed: int = 42
) -> dict[str, float | int | str]:
    environment = TrafficEnvironment(config)
    state = environment.reset(seed)
    done = False
    started_at = time.perf_counter()
    while not done:
        action = agent.choose_action(state, explore=False)
        result = environment.step(action)
        state = result.state
        done = result.done
    metrics = environment.metrics()
    metrics["inference_time_seconds"] = time.perf_counter() - started_at
    return metrics


def compare_controllers(
    config: ProjectConfig,
    q_agent: TabularAgent,
    sarsa_agent: TabularAgent,
    seeds: list[int],
) -> list[dict[str, float | int | str]]:
    rows = []
    for seed in seeds:
        fixed = run_fixed_time(config, seed)
        fixed["controller"] = "Fixed Time"
        fixed["seed"] = seed
        q_metrics = evaluate_agent(q_agent, config, seed)
        q_metrics["controller"] = "Q-Learning"
        q_metrics["seed"] = seed
        sarsa_metrics = evaluate_agent(sarsa_agent, config, seed)
        sarsa_metrics["controller"] = "SARSA"
        sarsa_metrics["seed"] = seed
        rows.extend([fixed, q_metrics, sarsa_metrics])
    return rows
