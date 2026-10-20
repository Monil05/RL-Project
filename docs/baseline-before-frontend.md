# Baseline recorded before the FastAPI and React work

Recorded on 20 October 2026. This directory was not a Git repository, so there was no commit, branch, or uncommitted diff to preserve. Protected files were hashed instead of being copied or rewritten.

## Existing tests

Command: `python -m pytest -q`

Result: 9 passed, 1 failed.

Pre-existing failure, not caused by the new application:

- `tests/test_project.py::test_live_svg_contains_lights_and_vehicle_routes`
- The SVG from `visualization/live_simulation.py` does not contain `data-start-angle`.
- This test was not changed and the renderer was not changed.

## Representative controller run

Configuration: default signal, reward, and learning rates, with `episodes=3`, `duration_seconds=40`, and training seed `42`. Evaluation seed `42`.

| Controller | Avg wait (s) | Avg queue | Throughput | Switches | Reward | Safety violations |
| --- | --- | --- | --- | --- | --- | --- |
| Fixed Time | 0.45 | 0.225 | 20 | 0 | 30.5 | 0 |
| Q-Learning | 0.45 | 0.225 | 20 | 0 | 30.5 | 0 |
| SARSA | 0.45 | 0.225 | 20 | 0 | 30.5 | 0 |

Q-Learning training took about 0.032 seconds. SARSA training took about 0.020 seconds. The first training episode for both algorithms matched the Fixed Time row above. These controllers are not being treated as different on this short run.

Historical files `results/experiment_results.csv` and `results/experiment_summary.csv` were left unchanged. In the saved summary, most scenarios are identical across controllers. The high-traffic summary is the visible exception: Q-Learning average waiting time is about 1.048 versus 1.043 for Fixed Time and SARSA, with 0.5 switches versus 0.

## Protected file SHA-256

- `690a2b13ba0972538fdf7d6b5f8274cf34137c90ab1877317ae8d29416ac78d2` `agents/q_learning.py`
- `7f43596a666195d5ae1c0cc2f54ccb83dcfbe4b8b3bda5a011f40d191eaf70e3` `agents/sarsa.py`
- `6b6f04af8edc8a9e71f76e1acd772bec21fbb9e156444d3712327dbd3c643c92` `agents/tabular_agent.py`
- `59d0e3269b10cca95a6a35ed48afa69ab25feef1fe03c2bdb7ba940fc2d4725b` `agents/__init__.py`
- `bd9de5d92bb08ee0665faa2b92e388cbe1499a50125cb9d0c037ab6ec3a00b1d` `environment/traffic_environment.py`
- `c8f4ff0579ddd5b5490847bc39180b1e17ec3381c866959c6685874586d3f45f` `environment/signal_controller.py`
- `faaa2d73e11132cf1d06044c0c3b4c50a1aad396721b6484e3585b9f40f34720` `environment/gym_env.py`
- `f48f494bd004f908d5b8a33a1ab0845b55ae7fa03305d8e17cc054a14a1e848c` `environment/__init__.py`
- `e93694ad2a6fcfdbf192cf6e9c7565b9a234aceabb48d0980f82a9ffd559d891` `baseline.py`
- `c8cb11228dc963864434119dc438b711962036bc1f4a897c415befefe07a491b` `training/train.py`
- `a7f81dd03f04ee5480535fc4fe33a69ad89718c595c17a13f1ad7687467fed24` `training/__init__.py`
- `6efc3d6300061260db4388d0be8e64aac1f6f6ceec4a3f349596b15818224a63` `evaluation/evaluate.py`
- `1bf1ef8d5675c8800ccdba5978536e1a42078df8fe6f0469ebf2893eb0b144d1` `evaluation/__init__.py`
- `6c98c3747cca927754a1ff1023a77a8cb56a476bf71a23bfb8ef172dd9f26734` `config.py`
- `6dc01dd1c04db2f4e97d7b57552500732f4f81ecb0dffb28539c39cd1e6af713` `experiments.py`
- `67813547534cfcf486517d8d450f91c73b533f67f81ccde3d5cc59205cbce0bc` `main.py`
- `451cb1d609b7f5e08d8c2b6dd5d260cf50da86516eeedc994b7cf60148c42789` `results/experiment_results.csv`
- `13d482737a0d4942bf942fba84f3e491c869307cdb8be9cd975fca037ca44bd2` `results/experiment_summary.csv`
