from agents.tabular_agent import TabularAgent
from environment.signal_controller import Action


class SarsaAgent(TabularAgent):
    def update(
        self,
        state: tuple[int, ...],
        action: Action,
        reward: float,
        next_state: tuple[int, ...],
        next_action: Action,
        done: bool,
    ) -> None:
        current_value = self.q_table[state][action]
        next_value = 0.0 if done else self.q_table[next_state][next_action]
        target = reward + self.config.discount_factor * next_value
        self.q_table[state][action] = current_value + self.config.learning_rate * (target - current_value)
