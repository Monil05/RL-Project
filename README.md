# Adaptive Traffic Signal Control Using Reinforcement Learning

This project implements a constrained reinforcement-learning controller for a four-way traffic intersection.

The project specification defines two safe signal phases:

- `NORTH_GREEN`, `SOUTH_GREEN`, `EAST_GREEN`, or `WEST_GREEN`

The controller will compare:

- Fixed-time control
- Q-Learning
- SARSA

Core timing defaults:

- Minimum green time: 10 seconds
- Maximum green time: 30 seconds
- Yellow interval: 3 seconds
- All-red clearance: 1 second
- Maximum waiting time: 90 seconds

## MDP Formulation

State:

- Queue length for North, South, East and West
- Oldest waiting time for North, South, East and West
- Current signal phase
- Elapsed green time

Actions:

- `KEEP`
- `SWITCH`

Reward:

- Negative queue penalty
- Negative waiting-time penalty
- Positive throughput reward
- Optional switching penalty

The environment enforces signal safety, so the agent cannot bypass yellow or all-red clearance. Early switch requests are blocked and counted separately from true safety violations.

## Project Structure

- `environment/traffic_environment.py`: vehicle arrivals, queues, movement, state, reward and metrics
- `environment/signal_controller.py`: signal phases, legal switching, yellow/all-red sequence and timing constraints
- `agents/q_learning.py`: tabular Q-Learning
- `agents/sarsa.py`: tabular SARSA
- `baseline.py`: fixed-time controller
- `training/train.py`: training loops
- `evaluation/evaluate.py`: controller comparison
- `experiments.py`: reproducible experiment runner
- `visualization/visualization.py`: Matplotlib plots
- `frontend/app.py`: Streamlit dashboard
- `config.py`: central configuration

## Run

```bash
python main.py
```

## Test

```bash
python -m pytest
```

## Launch Frontend

```bash
streamlit run frontend/app.py
```

The frontend is a live frame-by-frame demonstration. It supports:

- Start, stop and reset controls
- Fixed Time, Q-Learning and SARSA
- Low, medium, high, balanced, asymmetric and unseen traffic scenarios
- 2-lane and 4-lane visual layouts
- India-oriented free-left-turn behavior
- Queued and moving vehicles with left, straight and right route labels
- Live signal lights, queue metrics, waiting time, throughput, switches and reward

## Experiments

`experiments.py` runs scenario comparisons for fixed-time, Q-Learning and SARSA under low, medium, high, balanced, asymmetric and unseen traffic patterns. It also includes maximum-green and maximum-waiting-time sweeps.

```bash
python run_experiments.py
```

This writes:

- `results/experiment_results.csv`
- `results/experiment_summary.csv`

## Limitations

This is a compact academic simulator, not a microscopic traffic tool such as SUMO. DQN is intentionally left optional because the tabular Q-Learning and SARSA implementation is the required stable core.
