from collections import defaultdict
from random import Random

from config import LearningConfig
from environment.signal_controller import Action


class TabularAgent:
    def __init__(self, config: LearningConfig, seed: int = 42):
        self.config = config
        self.random = Random(seed)
        self.epsilon = config.epsilon
        self.q_table: dict[tuple[int, ...], dict[Action, float]] = defaultdict(self._new_action_values)

    def choose_action(self, state: tuple[int, ...], explore: bool = True) -> Action:
        if explore and self.random.random() < self.epsilon:
            return self.random.choice(list(Action))
        action_values = self.q_table[state]
        return max(action_values, key=action_values.get)

    def decay_epsilon(self) -> None:
        self.epsilon = max(self.config.minimum_epsilon, self.epsilon * self.config.epsilon_decay)

    def _new_action_values(self) -> dict[Action, float]:
        return {Action.KEEP: 0.0, Action.SWITCH: 0.0}
