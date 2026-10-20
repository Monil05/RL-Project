from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.router import router
from backend.app.bootstrap import APP_VERSION, RESULTS_DIR
from backend.app.services.errors import ApiError
from backend.app.services.results_service import ResultsService
from backend.app.services.simulation_service import SimulationService
from backend.app.services.training_service import TrainingService
from backend.app.services.video_service import VideoService


@asynccontextmanager
async def lifespan(app: FastAPI):
    training = TrainingService()
    simulation = SimulationService()
    simulation.bind_agents(training)
    app.state.training = training
    app.state.simulation = simulation
    app.state.video = VideoService(training)
    app.state.results = ResultsService(RESULTS_DIR)
    yield
    simulation.shutdown()


app = FastAPI(
    title="Adaptive Traffic Signal Control API",
    version=APP_VERSION,
    summary="HTTP adapter around the existing traffic simulation, Q-Learning, and SARSA code.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router)


@app.exception_handler(ApiError)
async def handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})
