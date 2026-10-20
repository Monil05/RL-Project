from dataclasses import replace

from config import DEFAULT_CONFIG, ProjectConfig, TRAFFIC_SCENARIOS
from evaluation.evaluate import compare_controllers
from training.train import config_with_arrival_rates, train_q_learning, train_sarsa


def run_core_experiments(config: ProjectConfig = DEFAULT_CONFIG) -> list[dict[str, float | int | str]]:
    results = []
    for scenario_name in ("low", "medium", "high", "balanced", "asymmetric", "unseen"):
        scenario_config = config_with_arrival_rates(config, TRAFFIC_SCENARIOS[scenario_name])
        q_agent, _ = train_q_learning(scenario_config)
        sarsa_agent, _ = train_sarsa(scenario_config)
        for row in compare_controllers(scenario_config, q_agent, sarsa_agent, seeds=[10, 20]):
            row["experiment"] = "traffic_scenario"
            row["scenario"] = scenario_name
            results.append(row)

    for maximum_green in (20, 30, 40, 60):
        signal = replace(config.signal, maximum_green_time=maximum_green)
        experiment_config = replace(config, signal=signal)
        q_agent, _ = train_q_learning(experiment_config)
        sarsa_agent, _ = train_sarsa(experiment_config)
        for row in compare_controllers(experiment_config, q_agent, sarsa_agent, seeds=[30]):
            row["experiment"] = "maximum_green"
            row["scenario"] = str(maximum_green)
            results.append(row)

    for maximum_wait in (60, 90, 120):
        signal = replace(config.signal, maximum_waiting_time=maximum_wait)
        experiment_config = replace(config, signal=signal)
        q_agent, _ = train_q_learning(experiment_config)
        sarsa_agent, _ = train_sarsa(experiment_config)
        for row in compare_controllers(experiment_config, q_agent, sarsa_agent, seeds=[40]):
            row["experiment"] = "maximum_wait"
            row["scenario"] = str(maximum_wait)
            results.append(row)

    return results
