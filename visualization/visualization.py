import matplotlib.pyplot as plt

from environment.traffic_environment import TrafficEnvironment, DIRECTIONS


def plot_training_history(history: list[dict[str, float | int]], value_name: str = "reward"):
    figure, axis = plt.subplots(figsize=(7, 4))
    axis.plot([row["episode"] for row in history], [row[value_name] for row in history])
    axis.set_xlabel("Episode")
    axis.set_ylabel(value_name.replace("_", " ").title())
    axis.grid(True, alpha=0.3)
    return figure


def plot_intersection(environment: TrafficEnvironment):
    figure, axis = plt.subplots(figsize=(5, 5))
    axis.axhline(0, color="black", linewidth=24, alpha=0.25)
    axis.axvline(0, color="black", linewidth=24, alpha=0.25)
    positions = {
        "north": (0, 2.5),
        "south": (0, -2.5),
        "east": (2.5, 0),
        "west": (-2.5, 0),
    }
    for direction in DIRECTIONS:
        x, y = positions[direction]
        axis.scatter([x], [y], s=80 + len(environment.queues[direction]) * 30)
        axis.text(x, y, f"{direction.title()}\n{len(environment.queues[direction])}", ha="center")
    axis.set_title(f"Signal: {environment.signal.current_phase.name}")
    axis.set_xlim(-4, 4)
    axis.set_ylim(-4, 4)
    axis.set_xticks([])
    axis.set_yticks([])
    return figure
