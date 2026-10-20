from typing import Literal

from pydantic import BaseModel, Field


class SimulationConfigRequest(BaseModel):
    algorithm: Literal["Fixed Time", "Q-Learning", "SARSA"] = "Fixed Time"
    scenario: str = "medium"
    lane_count: Literal[2, 4] = 2
    free_left_turn: bool = True
    duration_seconds: int = Field(300, ge=1, le=3600)
    seed: int = Field(42, ge=0, le=2_147_483_647)
    speed: float = Field(1.0, ge=0.25, le=4.0)
    agent_job_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "algorithm": "Fixed Time",
                    "scenario": "medium",
                    "lane_count": 2,
                    "free_left_turn": True,
                    "duration_seconds": 60,
                    "seed": 42,
                    "speed": 1.0,
                }
            ]
        }
    }


class TrainingStartRequest(BaseModel):
    algorithm: Literal["Q-Learning", "SARSA"]
    scenario: str = "medium"
    lane_count: Literal[2, 4] = 2
    free_left_turn: bool = True
    duration_seconds: int = Field(300, ge=1, le=3600)
    seed: int = Field(42, ge=0, le=2_147_483_647)
    episodes: int | None = Field(None, ge=1, le=1000)
    learning_rate: float | None = Field(None, ge=0.0, le=1.0)
    discount_factor: float | None = Field(None, ge=0.0, le=1.0)
    epsilon: float | None = Field(None, ge=0.0, le=1.0)
    epsilon_decay: float | None = Field(None, ge=0.0, le=1.0)
    minimum_epsilon: float | None = Field(None, ge=0.0, le=1.0)

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "algorithm": "Q-Learning",
                    "scenario": "high",
                    "episodes": 20,
                    "duration_seconds": 60,
                    "seed": 42,
                }
            ]
        }
    }


class VideoStartRequest(BaseModel):
    algorithm: Literal["Fixed Time", "Q-Learning", "SARSA"] = "Fixed Time"
    scenario: str = "medium"
    lane_count: Literal[2, 4] = 2
    free_left_turn: bool = True
    duration_seconds: int = Field(20, ge=1, le=3600)
    seed: int = Field(42, ge=0, le=2_147_483_647)
    fps: int = Field(10, ge=1, le=60)
    frames_per_step: int = Field(2, ge=1, le=30)
    agent_job_id: str | None = None

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "algorithm": "Fixed Time",
                    "scenario": "low",
                    "duration_seconds": 8,
                    "fps": 8,
                    "frames_per_step": 1,
                }
            ]
        }
    }
