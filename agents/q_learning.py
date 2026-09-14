from agents.tabular_agent import TabularAgent
from environment.signal_controller import Action


class QLearningAgent(TabularAgent):
    def update(
        self,
        state: tuple[int, ...],
        action: Action,
        reward: float,
        next_state: tuple[int, ...],
        done: bool,
    ) -> None:
        current_value = self.q_table[state][action]
        best_next_value = 0.0 if done else max(self.q_table[next_state].values())
        target = reward + self.config.discount_factor * best_next_value
        self.q_table[state][action] = current_value + self.config.learning_rate * (target - current_value)
