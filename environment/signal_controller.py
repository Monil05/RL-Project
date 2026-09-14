from dataclasses import dataclass
from enum import Enum

from config import SignalConfig


class SignalPhase(Enum):
    NORTH_GREEN = 0
    SOUTH_GREEN = 1
    EAST_GREEN = 2
    WEST_GREEN = 3
    YELLOW = 4
    ALL_RED = 5
    NS_GREEN = NORTH_GREEN
    EW_GREEN = EAST_GREEN


class Action(Enum):
    KEEP = 0
    SWITCH = 1


@dataclass
class SignalController:
    config: SignalConfig
    current_phase: SignalPhase = SignalPhase.ALL_RED
    elapsed_green_time: int = 0
    transition_timer: int = 0
    next_green_phase: SignalPhase | None = None
    active_direction: str | None = "north"
    next_green_direction: str | None = None
    switches: int = 0
    safety_violations: int = 0
    illegal_switch_attempts: int = 0
    demand_directions: tuple[str, ...] = ()

    def reset(self) -> None:
        self.current_phase = SignalPhase.ALL_RED
        self.elapsed_green_time = 0
        self.transition_timer = 0
        self.next_green_phase = None
        self.active_direction = None
        self.next_green_direction = None
        self.demand_directions = ()
        self.switches = 0
        self.safety_violations = 0
        self.illegal_switch_attempts = 0

    def green_directions(self) -> tuple[str, ...]:
        if self.current_phase in (
            SignalPhase.NORTH_GREEN,
            SignalPhase.SOUTH_GREEN,
            SignalPhase.EAST_GREEN,
            SignalPhase.WEST_GREEN,
        ) and self.active_direction in self.demand_directions:
            return (self.active_direction,)
        return ()

    def is_green_phase(self) -> bool:
        return self.current_phase in (
            SignalPhase.NORTH_GREEN,
            SignalPhase.SOUTH_GREEN,
            SignalPhase.EAST_GREEN,
            SignalPhase.WEST_GREEN,
        )

    def can_switch(self) -> bool:
        return self.is_green_phase() and self.elapsed_green_time >= self.config.minimum_green_time

    def update(
        self,
        action: Action,
        starvation_phase: SignalPhase | None = None,
        requested_direction: str | None = None,
        demand_directions: tuple[str, ...] | None = None,
    ) -> bool:
        switched = False
        self.demand_directions = demand_directions or ()

        if self.current_phase == SignalPhase.YELLOW:
            self.transition_timer -= 1
            if self.transition_timer <= 0:
                self.current_phase = SignalPhase.ALL_RED
                self.transition_timer = self.config.all_red_clearance
            return switched

        if self.current_phase == SignalPhase.ALL_RED:
            self.transition_timer -= 1
            if self.transition_timer <= 0 and self.next_green_phase is not None:
                self.current_phase = self.next_green_phase
                if self.next_green_direction is not None:
                    self.active_direction = self.next_green_direction
                self.next_green_phase = None
                self.next_green_direction = None
                self.elapsed_green_time = 0
            elif self.transition_timer <= 0 and requested_direction is not None:
                self.active_direction = requested_direction
                self.current_phase = self._phase_for_direction(requested_direction)
                self.elapsed_green_time = 0
            return switched

        active_has_demand = self.active_direction in self.demand_directions
        if not active_has_demand and requested_direction is not None:
            self.active_direction = requested_direction
            self.current_phase = self._phase_for_direction(requested_direction)
            self.elapsed_green_time = 0

        must_switch = self.elapsed_green_time >= self.config.maximum_green_time
        should_switch_for_starvation = (
            starvation_phase is not None
            and starvation_phase != self.current_phase
            and self.active_direction is not None
        )
        requested_switch = action == Action.SWITCH or must_switch or should_switch_for_starvation

        if (
            demand_directions is not None
            and not demand_directions
            and self.elapsed_green_time >= self.config.minimum_green_time
            and action == Action.KEEP
        ):
            self.current_phase = SignalPhase.ALL_RED
            self.transition_timer = self.config.all_red_clearance
            self.next_green_phase = None
            self.next_green_direction = None
            return switched

        if requested_switch and not self.can_switch() and not must_switch:
            self.illegal_switch_attempts += 1
            requested_switch = False

        if requested_switch:
            next_direction = requested_direction or self._alternate_direction()
            if next_direction == self.active_direction and demand_directions:
                alternatives = tuple(
                    direction for direction in demand_directions if direction != self.active_direction
                )
                if alternatives:
                    next_direction = alternatives[0]
                elif not must_switch:
                    requested_switch = False
            if not requested_switch:
                self.elapsed_green_time += 1
                return switched
            self.next_green_direction = next_direction
            self.next_green_phase = self._phase_for_direction(next_direction)
            self.current_phase = SignalPhase.YELLOW
            self.transition_timer = self.config.yellow_interval
            self.switches += 1
            switched = True
        else:
            self.elapsed_green_time += 1

        return switched

    def _alternate_direction(self) -> str:
        directions = ("north", "east", "south", "west")
        if self.active_direction not in directions:
            return directions[0]
        return directions[(directions.index(self.active_direction) + 1) % len(directions)]

    def _phase_for_direction(self, direction: str) -> SignalPhase:
        return {
            "north": SignalPhase.NORTH_GREEN,
            "south": SignalPhase.SOUTH_GREEN,
            "east": SignalPhase.EAST_GREEN,
            "west": SignalPhase.WEST_GREEN,
        }[direction]
