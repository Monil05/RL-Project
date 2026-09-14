from baseline import run_fixed_time
from config import DEFAULT_CONFIG
from evaluation.evaluate import compare_controllers
from training.train import train_q_learning, train_sarsa


def main() -> None:
    config = DEFAULT_CONFIG
    q_agent, q_history = train_q_learning(config)
    sarsa_agent, sarsa_history = train_sarsa(config)
    rows = compare_controllers(config, q_agent, sarsa_agent, seeds=[config.simulation.random_seed])

    print("Adaptive Traffic Signal Control Using Reinforcement Learning")
    print(f"Fixed-time baseline throughput: {run_fixed_time(config)['throughput']}")
    print(f"Q-Learning episodes trained: {len(q_history)}")
    print(f"SARSA episodes trained: {len(sarsa_history)}")
    for row in rows:
        print(
            f"{row['controller']}: avg_wait={row['average_waiting_time']:.2f}, "
            f"avg_queue={row['average_queue_length']:.2f}, throughput={row['throughput']}"
        )


if __name__ == "__main__":
    main()
