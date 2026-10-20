from pathlib import Path

import pandas as pd

from experiments import run_core_experiments


def main() -> None:
    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)

    results = run_core_experiments()
    results_frame = pd.DataFrame(results)
    results_frame.to_csv(results_dir / "experiment_results.csv", index=False)

    summary = results_frame.groupby(["experiment", "scenario", "controller"], as_index=False)[
        [
            "average_waiting_time",
            "maximum_waiting_time",
            "average_queue_length",
            "maximum_queue_length",
            "throughput",
            "number_of_switches",
            "safety_violations",
            "cumulative_reward",
        ]
    ].mean()
    summary.to_csv(results_dir / "experiment_summary.csv", index=False)

    print("Experiment results saved to results/experiment_results.csv")
    print("Experiment summary saved to results/experiment_summary.csv")


if __name__ == "__main__":
    main()
