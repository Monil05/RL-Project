from config import ProjectConfig
from environment.signal_controller import Action
from environment.traffic_environment import TrafficEnvironment


class FixedTimeController:
    def __init__(self, fixed_green_duration: int):
        self.fixed_green_duration = fixed_green_duration

    def choose_action(self, environment: TrafficEnvironment) -> Action:
        if (
            environment.signal.elapsed_green_time >= self.fixed_green_duration
            and environment.signal.can_switch()
        ):
            return Action.SWITCH
        return Action.KEEP


def run_fixed_time(config: ProjectConfig, seed: int = 42) -> dict[str, float | int | str]:
    environment = TrafficEnvironment(config)
    environment.reset(seed)
    controller = FixedTimeController(config.signal.maximum_green_time)
    done = False
    while not done:
        result = environment.step(controller.choose_action(environment))
        done = result.done
    return environment.metrics()
