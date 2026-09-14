import base64
from pathlib import Path

from environment.signal_controller import Action, SignalPhase
from environment.traffic_environment import DIRECTIONS, Movement, TrafficEnvironment, Vehicle


CANVAS_SIZE = 760
CENTER = CANVAS_SIZE / 2
CAR_ASSET = Path(__file__).resolve().parents[1] / "frontend" / "assets" / "car.svg"
CAR_DATA_URI = "data:image/svg+xml;base64," + base64.b64encode(CAR_ASSET.read_bytes()).decode("ascii")


def create_active_movements(vehicles: list[Vehicle]) -> list[dict[str, str | float | int]]:
    return [
        {
            "vehicle_id": vehicle.vehicle_id,
            "direction": vehicle.direction,
            "movement": vehicle.movement.value,
            "lane_index": vehicle.lane_index,
            "progress": 0.0,
        }
        for vehicle in vehicles
    ]


def advance_active_movements(
    active_movements: list[dict[str, str | float | int]], progress_step: float
) -> list[dict[str, str | float | int]]:
    remaining_movements = []
    for movement in active_movements:
        movement["progress"] = min(1.0, float(movement["progress"]) + progress_step)
        if float(movement["progress"]) < 1.0:
            remaining_movements.append(movement)
    return remaining_movements


def render_live_intersection(
    environment: TrafficEnvironment,
    active_movements: list[dict[str, str | float | int]],
    lane_count: int,
    last_action: Action,
    algorithm_name: str,
) -> str:
    road_width = 170 if lane_count == 2 else 250
    svg_parts = [
        f"<svg viewBox='0 0 {CANVAS_SIZE} {CANVAS_SIZE}' width='100%' height='680' "
        "xmlns='http://www.w3.org/2000/svg'>",
        "<rect width='760' height='760' fill='#eef2f3'/>",
        _road_shapes(road_width),
        _lane_markings(lane_count, road_width),
        _traffic_lights(
            environment.signal.current_phase,
            environment.signal.active_direction if environment.signal.green_directions() else None,
            road_width,
        ),
        _queued_vehicles(environment, lane_count),
        _moving_vehicles(active_movements, lane_count),
        _browser_animation_script(),
        "</svg>",
    ]
    return "".join(svg_parts)


def _road_shapes(road_width: int) -> str:
    left = CENTER - road_width / 2
    return (
        f"<rect x='{left}' y='0' width='{road_width}' height='{CANVAS_SIZE}' fill='#3f4548'/>"
        f"<rect x='0' y='{left}' width='{CANVAS_SIZE}' height='{road_width}' fill='#3f4548'/>"
        f"<rect x='{left}' y='{left}' width='{road_width}' height='{road_width}' fill='#34393b'/>"
    )


def _lane_markings(lane_count: int, road_width: int) -> str:
    lines = []
    lane_total = 2 if lane_count == 2 else 4
    lane_width = road_width / lane_total
    start = CENTER - road_width / 2
    for index in range(1, lane_total):
        offset = start + lane_width * index
        dash = "10 12" if index != lane_total / 2 else "none"
        color = "#f4d35e" if index == lane_total / 2 else "#dfe5e7"
        edge = CENTER - road_width / 2
        far_edge = CENTER + road_width / 2
        lines.extend(
            [
                f"<line x1='{offset}' y1='0' x2='{offset}' y2='{edge}' stroke='{color}' stroke-width='3' stroke-dasharray='{dash}' opacity='0.9'/>",
                f"<line x1='{offset}' y1='{far_edge}' x2='{offset}' y2='{CANVAS_SIZE}' stroke='{color}' stroke-width='3' stroke-dasharray='{dash}' opacity='0.9'/>",
                f"<line x1='0' y1='{offset}' x2='{edge}' y2='{offset}' stroke='{color}' stroke-width='3' stroke-dasharray='{dash}' opacity='0.9'/>",
                f"<line x1='{far_edge}' y1='{offset}' x2='{CANVAS_SIZE}' y2='{offset}' stroke='{color}' stroke-width='3' stroke-dasharray='{dash}' opacity='0.9'/>",
            ]
        )
    stop = 120 if lane_count == 2 else 150
    lines.extend(
        [
            f"<line x1='{CENTER - road_width / 2}' y1='{CENTER - road_width / 2}' x2='{CENTER + road_width / 2}' y2='{CENTER - road_width / 2}' stroke='white' stroke-width='5'/>",
            f"<line x1='{CENTER - road_width / 2}' y1='{CENTER + road_width / 2}' x2='{CENTER + road_width / 2}' y2='{CENTER + road_width / 2}' stroke='white' stroke-width='5'/>",
            f"<line x1='{CENTER - road_width / 2}' y1='{CENTER - road_width / 2}' x2='{CENTER - road_width / 2}' y2='{CENTER + road_width / 2}' stroke='white' stroke-width='5'/>",
            f"<line x1='{CENTER + road_width / 2}' y1='{CENTER - road_width / 2}' x2='{CENTER + road_width / 2}' y2='{CENTER + road_width / 2}' stroke='white' stroke-width='5'/>",
        ]
    )
    return "".join(lines)


def _traffic_lights(phase: SignalPhase, active_direction: str | None, road_width: int) -> str:
    colors = {
        direction: _light_color(phase, active_direction, direction)
        for direction in ("north", "south", "east", "west")
    }
    return (
        _light_group(CENTER + road_width / 2 + 30, CENTER - road_width / 2 - 25, "NORTH", colors["north"])
        + _light_group(CENTER - road_width / 2 - 30, CENTER + road_width / 2 + 25, "SOUTH", colors["south"])
        + _light_group(CENTER + road_width / 2 + 25, CENTER + road_width / 2 + 30, "EAST", colors["east"])
        + _light_group(CENTER - road_width / 2 - 25, CENTER - road_width / 2 - 30, "WEST", colors["west"])
    )


def _light_color(phase: SignalPhase, active_direction: str, direction: str) -> str:
    if phase == SignalPhase.ALL_RED:
        return "#e63946"
    if phase == SignalPhase.YELLOW:
        return "#ffbe0b" if direction == active_direction else "#e63946"
    if direction == active_direction:
        return "#2dc653"
    return "#e63946"


def _light_group(x: float, y: float, label: str, color: str) -> str:
    lamps = {"#e63946": ("#f04452", "#42171b", "#42171b"), "#ffbe0b": ("#42171b", "#ffd166", "#1d3b24"), "#2dc653": ("#42171b", "#443a17", "#49e06e")}[color]
    return (
        f"<g><rect x='{x - 15}' y='{y - 36}' width='30' height='72' rx='7' fill='#15191b' stroke='#697278' stroke-width='2'/>"
        f"<circle cx='{x}' cy='{y - 22}' r='7' fill='{lamps[0]}'/><circle cx='{x}' cy='{y}' r='7' fill='{lamps[1]}'/><circle cx='{x}' cy='{y + 22}' r='7' fill='{lamps[2]}'/>"
        f"<text x='{x}' y='{y + 52}' text-anchor='middle' font-size='11' font-weight='700' fill='#101820'>{label}</text></g>"
    )


def _queued_vehicles(environment: TrafficEnvironment, lane_count: int) -> str:
    vehicles = []
    lane_slots: dict[tuple[str, int], int] = {}
    for direction in DIRECTIONS:
        for vehicle in environment.queues[direction]:
            key = (direction, vehicle.lane_index)
            lane_slots[key] = lane_slots.get(key, 0) + 1
            x, y = _queue_position(direction, vehicle.lane_index, lane_slots[key] - 1, lane_count)
            vehicles.append(
                _vehicle_shape(
                    x,
                    y,
                    _approach_angle(direction),
                    vehicle.movement,
                    queued=True,
                )
            )
    return "".join(vehicles)


def _moving_vehicles(active_movements: list[dict[str, str | float | int]], lane_count: int) -> str:
    vehicles = []
    for movement in active_movements:
        direction = str(movement["direction"])
        turn = Movement(str(movement["movement"]))
        lane_index = int(movement["lane_index"])
        progress = float(movement["progress"])
        x, y, angle = _route_pose(direction, turn, lane_index, progress, lane_count)
        target = _route_pose(direction, turn, lane_index, min(1.0, progress + 0.24), lane_count)
        vehicles.append(_vehicle_shape(x, y, angle, turn, queued=False, target=target))
    return "".join(vehicles)


def _queue_position(direction: str, lane_index: int, queue_index: int, lane_count: int) -> tuple[float, float]:
    x, y = _route_start(direction, lane_index, lane_count)
    spacing = 28
    if direction == "north":
        return x, y - spacing * queue_index
    if direction == "south":
        return x, y + spacing * queue_index
    if direction == "east":
        return x + spacing * queue_index, y
    return x - spacing * queue_index, y


def _route_pose(
    direction: str, movement: Movement, lane_index: int, progress: float, lane_count: int
) -> tuple[float, float, float]:
    start = _route_start(direction, lane_index, lane_count)
    end = _route_end(direction, movement, lane_count)
    if movement == Movement.STRAIGHT:
        x, y = _lerp_point(start, end, progress)
        angle = _approach_angle(direction)
        return x, y, angle

    control = _turn_control(direction, movement, lane_count)
    x, y = _quadratic_point(start, control, end, progress)
    tangent_x = 2 * (1 - progress) * (control[0] - start[0]) + 2 * progress * (end[0] - control[0])
    tangent_y = 2 * (1 - progress) * (control[1] - start[1]) + 2 * progress * (end[1] - control[1])
    angle = _screen_angle(tangent_x, tangent_y)
    return x, y, angle


def _turn_control(direction: str, movement: Movement, lane_count: int) -> tuple[float, float]:
    """Keep the turn arc on the vehicle's left-traffic side of the junction."""
    radius = 58 if lane_count == 2 else 76
    if direction == "north":
        return (CENTER - radius, CENTER - radius) if movement == Movement.LEFT else (CENTER + radius, CENTER - radius)
    if direction == "south":
        return (CENTER + radius, CENTER + radius) if movement == Movement.LEFT else (CENTER - radius, CENTER + radius)
    if direction == "east":
        return (CENTER + radius, CENTER - radius) if movement == Movement.LEFT else (CENTER + radius, CENTER + radius)
    return (CENTER - radius, CENTER + radius) if movement == Movement.LEFT else (CENTER - radius, CENTER - radius)


def _route_start(direction: str, lane_index: int, lane_count: int) -> tuple[float, float]:
    incoming_offset = 36 if lane_count == 2 else 42 + lane_index * 34
    stop_offset = 120 if lane_count == 2 else 150
    if direction == "north":
        return CENTER + incoming_offset, CENTER - stop_offset
    if direction == "south":
        return CENTER - incoming_offset, CENTER + stop_offset
    if direction == "east":
        return CENTER + stop_offset, CENTER + incoming_offset
    return CENTER - stop_offset, CENTER - incoming_offset


def _route_end(direction: str, movement: Movement, lane_count: int) -> tuple[float, float]:
    destination = _destination_direction(direction, movement)
    exit_offset = 36 if lane_count == 2 else 42
    if destination == "north":
        return CENTER - exit_offset, 40
    if destination == "south":
        return CENTER + exit_offset, CANVAS_SIZE - 40
    if destination == "east":
        return CANVAS_SIZE - 40, CENTER - exit_offset
    return 40, CENTER + exit_offset


def _destination_direction(direction: str, movement: Movement) -> str:
    destinations = {
        "north": {Movement.LEFT: "west", Movement.STRAIGHT: "south", Movement.RIGHT: "east"},
        "south": {Movement.LEFT: "east", Movement.STRAIGHT: "north", Movement.RIGHT: "west"},
        "east": {Movement.LEFT: "north", Movement.STRAIGHT: "west", Movement.RIGHT: "south"},
        "west": {Movement.LEFT: "south", Movement.STRAIGHT: "east", Movement.RIGHT: "north"},
    }
    return destinations[direction][movement]


def _approach_angle(direction: str) -> float:
    return {"north": 90.0, "south": 270.0, "east": 180.0, "west": 0.0}[direction]


def _screen_angle(dx: float, dy: float) -> float:
    import math

    return math.degrees(math.atan2(dy, dx))


def _lerp_point(start: tuple[float, float], end: tuple[float, float], progress: float) -> tuple[float, float]:
    return start[0] + (end[0] - start[0]) * progress, start[1] + (end[1] - start[1]) * progress


def _quadratic_point(
    start: tuple[float, float], control: tuple[float, float], end: tuple[float, float], progress: float
) -> tuple[float, float]:
    one_minus = 1 - progress
    x = one_minus * one_minus * start[0] + 2 * one_minus * progress * control[0] + progress * progress * end[0]
    y = one_minus * one_minus * start[1] + 2 * one_minus * progress * control[1] + progress * progress * end[1]
    return x, y


def _vehicle_shape(
    x: float,
    y: float,
    angle: float,
    movement: Movement,
    queued: bool,
    target: tuple[float, float, float] | None = None,
) -> str:
    opacity = "0.95" if queued else "1.0"
    label = {"left": "L", "straight": "S", "right": "R"}[movement.value]
    data = ""
    if target is not None:
        data = (
            f" data-start-x='{x:.3f}' data-start-y='{y:.3f}' data-start-angle='{angle:.3f}'"
            f" data-end-x='{target[0]:.3f}' data-end-y='{target[1]:.3f}' data-end-angle='{target[2]:.3f}'"
        )
    return (
        f"<g class='vehicle' opacity='{opacity}' aria-label='vehicle {label}'{data} transform='translate({x - 18:.2f} {y - 18:.2f}) rotate({angle:.2f} 18 18)'>"
        f"<image href='{CAR_DATA_URI}' x='0' y='0' width='36' height='36' preserveAspectRatio='xMidYMid meet'/>"
        f"<text x='0' y='0' opacity='0' aria-hidden='true'>{label}</text></g>"
    )


def _browser_animation_script() -> str:
    return (
        "<script><![CDATA[(function(){const cars=[...document.querySelectorAll('[data-end-x]')];"
        "const start=performance.now();function frame(now){const t=Math.min(1,(now-start)/240),q=t*t*(3-2*t);"
        "cars.forEach(car=>{const sx=+car.dataset.startX,sy=+car.dataset.startY,sa=+car.dataset.startAngle;"
        "const ex=+car.dataset.endX,ey=+car.dataset.endY,ea=+car.dataset.endAngle;"
        "car.setAttribute('transform',`translate(${sx+(ex-sx)*q-18} ${sy+(ey-sy)*q-18}) rotate(${sa+(ea-sa)*q} 18 18)`);});"
        "if(t<1)requestAnimationFrame(frame);}requestAnimationFrame(frame);})();]]></script>"
    )
