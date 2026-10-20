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
- `frontend/app.py`: original Streamlit dashboard, still available
- `backend/`: FastAPI adapter around the existing Python modules
- `web/`: React + Vite application
- `config.py`: central configuration

## Architecture

The browser does not simulate traffic. React polls FastAPI. FastAPI calls the existing `TrafficEnvironment`, `FixedTimeController`, `train_q_learning`, `train_sarsa`, and `generate_simulation_video` functions. Q-Learning and SARSA updates are unchanged.

```text
web (React, port 5173) -- /api --> backend (FastAPI, port 8000) --> existing Python core
```

There is no database and no authentication. Trained agents live in the API process memory. Experiment tables are read from the existing CSV files and are not rewritten by the API.

## Prerequisites

- Python 3.11 or newer (verified with 3.13)
- Node.js 20 or newer, with npm
- No separate FFmpeg install is required for the API. `imageio-ffmpeg` supplies the binary used by video export.

## Installation

From the repository root:

```bash
python -m pip install -r backend/requirements.txt
python -m pip install -r requirements.txt
cd web
npm install
```

`requirements.txt` is the original simulator list. `backend/requirements.txt` adds FastAPI, Uvicorn, Pillow, imageio, and pytest. The Streamlit package remains in the original file.

## Run the web application

Terminal 1, from the repository root:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal 2:

```bash
cd web
npm run dev
```

Open `http://127.0.0.1:5173`. The Vite dev server proxies `/api` to port 8000. Interactive API docs are at `http://127.0.0.1:8000/docs`.

Optional environment variable for a deployed frontend that cannot use the proxy:

```text
VITE_API_BASE=http://127.0.0.1:8000
```

Leave it unset during local development.

## Original commands

```bash
python main.py
python -m pytest
python run_experiments.py
streamlit run frontend/app.py
```

`python run_experiments.py` overwrites `results/experiment_results.csv` and `results/experiment_summary.csv`. The web application only reads those files. Do not run the experiment script if you need to keep the current result files.

## Tests

```bash
python -m pytest backend/tests
cd web
npm test
python -m pytest
```

`python -m pytest` also runs the original suite. One original test, `test_live_svg_contains_lights_and_vehicle_routes`, failed before this work because the SVG renderer does not emit `data-start-angle`. That renderer and that assertion were left unchanged.

## API

All responses use JSON unless noted. Errors use `{"detail": "..."}`.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/health` | `{"status":"ok","version":"1.0.0","service":"traffic-rl-api"}` |
| GET | `/api/project` | Algorithms, scenarios, and default signal, reward, learning, and simulation settings |
| GET | `/api/simulation/state` | Queues, signal, metrics, and time series from the live environment |
| GET | `/api/simulation/metrics` | Metrics only. `metrics` is null until a simulation is loaded |
| POST | `/api/simulation/configure` | Controller, scenario, lanes, free left turn, duration, seed, and speed |
| POST | `/api/simulation/start` | Start or resume. A second start does not create another ticker |
| POST | `/api/simulation/pause` | Pause. 409 if it is not running |
| POST | `/api/simulation/reset` | New environment at the selected seed, status idle |
| POST | `/api/simulation/step` | One simulation second. 409 while automatic playback is running |
| POST | `/api/training/start` | Background call to the existing Q-Learning or SARSA trainer. Returns 202 |
| GET | `/api/training/status/{job_id}` | Job status. History appears when the trainer returns |
| GET | `/api/training/jobs` | Jobs stored in this process |
| GET | `/api/training/agents` | Completed agents, without Q-tables |
| POST | `/api/training/cancel/{job_id}` | Cancels a queued job. 409 once training has started |
| GET | `/api/experiments` | Experiment names in the existing results CSV |
| GET | `/api/experiments/{experiment_id}` | Rows for one experiment name |
| GET | `/api/results` | Filter by `experiment`, `scenario`, `controller`, and `seed` |
| GET | `/api/results/summary` | Summary rows plus percent difference versus Fixed Time |
| GET | `/api/results/export` | Filtered CSV download. Does not modify the source file |
| POST | `/api/video/generate` | Background render. Returns 202 |
| GET | `/api/video/status/{job_id}` | Render status. No partial progress |
| POST | `/api/video/cancel/{job_id}` | Cancels a queued render. 409 after rendering starts |
| GET | `/api/video/{job_id}/file` | MP4 for a completed job |

Configure example:

```bash
curl -X POST http://127.0.0.1:8000/api/simulation/configure -H "Content-Type: application/json" -d "{\"algorithm\":\"Fixed Time\",\"scenario\":\"medium\",\"duration_seconds\":60,\"seed\":42,\"speed\":1}"
```

Training example. Omitted learning fields keep `LearningConfig` defaults, including 120 episodes:

```bash
curl -X POST http://127.0.0.1:8000/api/training/start -H "Content-Type: application/json" -d "{\"algorithm\":\"Q-Learning\",\"scenario\":\"low\",\"episodes\":2,\"duration_seconds\":15,\"seed\":42}"
```

A percent difference is `(controller - fixed_time) / abs(fixed_time) * 100`. It is null when the Fixed Time value is missing or zero. Negative waiting time means a lower wait than Fixed Time on that row only.

## Video generation

The existing exporter keeps every frame in memory. The API rejects requests above 400 frames (`duration_seconds * frames_per_step`). The Video page starts from a short clip for that reason. The project simulation default remains 300 seconds. Completed files are stored under `generated/videos/` and downloaded by job id. The response does not expose a filesystem path.

Q-Learning and SARSA clips require a completed in-memory agent for the same scenario and lane layout.

## Experiments

`experiments.py` runs scenario comparisons for fixed-time, Q-Learning and SARSA under low, medium, high, balanced, asymmetric and unseen traffic patterns. It also includes maximum-green and maximum-waiting-time sweeps.

```bash
python run_experiments.py
```

This writes:

- `results/experiment_results.csv`
- `results/experiment_summary.csv`

The saved summary does not show a general advantage for Q-Learning or SARSA. On the high-demand rows, Q-Learning's average waiting time is slightly higher than Fixed Time and SARSA. Most other stored scenarios match across the three controllers.

## Troubleshooting

- The React page says the API is unreachable: start Uvicorn on port 8000, then use Retry connection.
- Q-Learning or SARSA will not start: train that algorithm for the same scenario and lane count first. Agents disappear when the API process stops.
- Training has no episode counter while it runs: the existing training functions return history only at the end. Cancel works only while the job is still queued.
- Video generation fails: read the job error. A missing Pillow, imageio, or FFmpeg plugin is reported as a failed job, not as a finished video.
- `python -m pytest` reports `data-start-angle`: that failure is pre-existing in the Streamlit SVG test.

## Limitations

This is a compact academic simulator, not a microscopic traffic tool such as SUMO. DQN is intentionally left optional because the tabular Q-Learning and SARSA implementation is the required stable core.

The web application does not add a second traffic model. Moving vehicles between simulation seconds are interpolated for display. Metrics, queues, and signal phases come from Python. The original Streamlit app is still launched with `streamlit run frontend/app.py`.
