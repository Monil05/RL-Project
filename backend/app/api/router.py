"""HTTP routes. Each handler delegates to an existing Python service."""

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, PlainTextResponse

from backend.app.bootstrap import APP_VERSION
from backend.app.schemas.models import SimulationConfigRequest, TrainingStartRequest, VideoStartRequest
from backend.app.services.config_factory import defaults_payload

router = APIRouter(prefix="/api")


def _sim(request: Request):
    return request.app.state.simulation


def _training(request: Request):
    return request.app.state.training


def _video(request: Request):
    return request.app.state.video


def _results(request: Request):
    return request.app.state.results


@router.get("/health", tags=["health"], summary="Process health")
def health() -> dict:
    """Returns application version and a static ok status. It does not run the simulation."""
    return {"status": "ok", "version": APP_VERSION, "service": "traffic-rl-api"}


@router.get("/project", tags=["project"], summary="Algorithms, scenarios, and default configuration")
def project() -> dict:
    """Returns the existing default configuration. This does not modify those defaults."""
    payload = defaults_payload()
    payload["version"] = APP_VERSION
    payload["streamlit_frontend"] = "streamlit run frontend/app.py"
    return payload


@router.get("/simulation/state", tags=["simulation"], summary="Current simulation state")
def simulation_state(request: Request) -> dict:
    """Queue contents, signal phase, and metrics come from the live TrafficEnvironment."""
    return _sim(request).snapshot()


@router.get("/simulation/metrics", tags=["simulation"], summary="Current metrics only")
def simulation_metrics(request: Request) -> dict:
    """Same metrics object as the state payload. Null until a simulation is loaded."""
    state = _sim(request).snapshot()
    return {"ready": state["ready"], "status": state["status"], "metrics": state["metrics"]}


@router.post("/simulation/configure", tags=["simulation"], summary="Update controller, demand, and speed")
def simulation_configure(payload: SimulationConfigRequest, request: Request) -> dict:
    """Speed can change during playback. Controller and demand changes require a reset."""
    return _sim(request).configure(payload)


@router.post("/simulation/start", tags=["simulation"], summary="Start or resume playback")
def simulation_start(request: Request) -> dict:
    """Starts the single ticker. A second start while running returns the current state."""
    return _sim(request).start()


@router.post("/simulation/pause", tags=["simulation"], summary="Pause playback")
def simulation_pause(request: Request) -> dict:
    """Stops automatic steps. The environment is left where it is."""
    return _sim(request).pause()


@router.post("/simulation/reset", tags=["simulation"], summary="Reset the environment")
def simulation_reset(request: Request) -> dict:
    """Creates a new environment with the current configuration and the selected seed."""
    return _sim(request).reset()


@router.post("/simulation/step", tags=["simulation"], summary="Advance one simulation second")
def simulation_step(request: Request) -> dict:
    """Manual step for tests and inspection. Rejected while automatic playback is running."""
    return _sim(request).step()


@router.post("/training/start", tags=["training"], summary="Start Q-Learning or SARSA training", status_code=202)
def training_start(payload: TrainingStartRequest, request: Request) -> dict:
    """Runs the existing training function on a background thread. Omitted hyperparameters keep their defaults."""
    return _training(request).start(payload)


@router.get("/training/status/{job_id}", tags=["training"], summary="Training job status")
def training_status(job_id: str, request: Request) -> dict:
    """History is present only after the existing training function returns."""
    return _training(request).status(job_id)


@router.get("/training/jobs", tags=["training"], summary="List training jobs in this process")
def training_jobs(request: Request) -> dict:
    """In-memory jobs. They are cleared when the API process stops."""
    return {"jobs": _training(request).list_jobs()}


@router.get("/training/agents", tags=["training"], summary="Completed agents in this process")
def training_agents(request: Request) -> dict:
    """Agents that can be selected by the simulation. Q-tables are not included."""
    return {"agents": _training(request).list_agents()}


@router.post("/training/cancel/{job_id}", tags=["training"], summary="Cancel a queued training job")
def training_cancel(job_id: str, request: Request) -> dict:
    """Cancels a job that has not entered the trainer. A running trainer returns 409."""
    return _training(request).cancel(job_id)


@router.get("/experiments", tags=["results"], summary="Experiment groups in the existing CSV")
def experiments(request: Request) -> dict:
    """Reads results/experiment_results.csv. It does not run a new experiment."""
    return _results(request).experiments()


@router.get("/experiments/{experiment_id}", tags=["results"], summary="Records for one experiment name")
def experiment_detail(experiment_id: str, request: Request) -> dict:
    """Returns the stored rows whose experiment column equals the path value."""
    return _results(request).experiment(experiment_id)


@router.get("/results", tags=["results"], summary="Filter stored evaluation rows")
def results(
    request: Request,
    experiment: str | None = None,
    scenario: str | None = None,
    controller: str | None = None,
    seed: str | None = None,
) -> dict:
    """Filters are exact matches against the existing results file."""
    return _results(request).results(experiment=experiment, scenario=scenario, controller=controller, seed=seed)


@router.get("/results/summary", tags=["results"], summary="Filtered summary with Fixed Time differences")
def results_summary(
    request: Request,
    experiment: str | None = None,
    scenario: str | None = None,
    controller: str | None = None,
) -> dict:
    """Percentage differences are null when the Fixed Time baseline is missing or zero."""
    return _results(request).summary(experiment=experiment, scenario=scenario, controller=controller)


@router.get("/results/export", tags=["results"], summary="Download filtered results as CSV")
def results_export(
    request: Request,
    experiment: str | None = None,
    scenario: str | None = None,
    controller: str | None = None,
    seed: str | None = None,
):
    """Builds a new CSV response. It does not modify results/experiment_results.csv."""
    body = _results(request).export_csv(experiment=experiment, scenario=scenario, controller=controller, seed=seed)
    return PlainTextResponse(
        body,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=results-export.csv"},
    )


@router.post("/video/generate", tags=["video"], summary="Start a video render", status_code=202)
def video_generate(payload: VideoStartRequest, request: Request) -> dict:
    """Calls generate_simulation_video in the background. Large frame counts are rejected."""
    return _video(request).start(payload)


@router.get("/video/status/{job_id}", tags=["video"], summary="Video job status")
def video_status(job_id: str, request: Request) -> dict:
    """The existing renderer does not report partial progress."""
    return _video(request).status(job_id)


@router.post("/video/cancel/{job_id}", tags=["video"], summary="Cancel a queued video job")
def video_cancel(job_id: str, request: Request) -> dict:
    """Cancels a job that has not entered the renderer. A running render returns 409."""
    return _video(request).cancel(job_id)


@router.get("/video/{job_id}/file", tags=["video"], summary="Download a completed video")
def video_file(job_id: str, request: Request):
    """Streams the mp4 created for this job id. Paths are not taken from the client."""
    path = _video(request).file_path(job_id)
    return FileResponse(path, media_type="video/mp4", filename=f"{job_id}.mp4")
