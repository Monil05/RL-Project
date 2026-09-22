"""Gymnasium API wrapper for the Traffic Environment.

Conforms to standard Gymnasium Env interface (gymnasium.Env).
"""

from typing import Any

import gymnasium as gym
from gymnasium import spaces
import numpy as np

from config import DEFAULT_CONFIG, ProjectConfig
from environment.traffic_environment import TrafficEnvironment, DIRECTIONS, Movement
from environment.signal_controller import Action


class TrafficGymEnv(gym.Env):
    """Gymnasium Environment wrapper for Adaptive Traffic Signal Control."""

    metadata = {"render_modes": ["rgb_array"], "render_fps": 30}

    def __init__(self, config: ProjectConfig = DEFAULT_CONFIG, render_mode: str | None = None):
        super().__init__()
        self.config = config
        self.render_mode = render_mode
        self.env = TrafficEnvironment(config)

        # Action space: 0 = KEEP, 1 = SWITCH
        self.action_space = spaces.Discrete(2)

        # Observation space: 4 queue bins [0-5], 4 wait bins [0-6], 1 phase [0-5], 1 green bin [0-6]
        low = np.array([0, 0, 0, 0, 0, 0, 0, 0, 0, 0], dtype=np.int32)
        high = np.array([5, 5, 5, 5, 6, 6, 6, 6, 5, 6], dtype=np.int32)
        self.observation_space = spaces.Box(low=low, high=high, dtype=np.int32)

    def reset(
        self,
        *,
        seed: int | None = None,
        options: dict[str, Any] | None = None,
    ) -> tuple[np.ndarray, dict[str, Any]]:
        super().reset(seed=seed)
        state_tuple = self.env.reset(seed=seed)
        obs = np.array(state_tuple, dtype=np.int32)
        info = self.env.metrics()
        return obs, info

    def step(self, action: int | Action) -> tuple[np.ndarray, float, bool, bool, dict[str, Any]]:
        act = Action(action) if isinstance(action, int) else action
        result = self.env.step(act)
        obs = np.array(result.state, dtype=np.int32)
        reward = float(result.reward)
        terminated = bool(result.done)
        truncated = False
        info = dict(result.info)
        return obs, reward, terminated, truncated, info

    def render(self) -> np.ndarray | None:
        if self.render_mode == "rgb_array":
            from visualization.video_renderer import render_env_frame
            return render_env_frame(self.env)
        return None
