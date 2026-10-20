"""Video exporter and frame renderer using PIL, Imageio, and FFmpeg.

Generates smooth 60/30 fps MP4 video files of the simulation with real RL agent actions.
"""

import math
import os
import tempfile
from pathlib import Path

import imageio.v3 as iio
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from baseline import FixedTimeController
from config import ProjectConfig
from environment.traffic_environment import DIRECTIONS, Movement, TrafficEnvironment, Vehicle


def render_env_frame(env: TrafficEnvironment, width: int = 800, height: int = 800) -> np.ndarray:
    """Render a single static state frame of the environment to an RGB numpy array."""
    img = Image.new("RGB", (width, height), "#0f172a")
    draw = ImageDraw.Draw(img)
    
    lane_count = env.config.simulation.lane_count
    phase = env.signal.current_phase.name
    active_dir = env.signal.active_direction
    
    _draw_intersection(draw, width, height, lane_count)
    _draw_lights(draw, width, height, phase, active_dir)
    _draw_queues(draw, width, height, env.queues, lane_count)
    _draw_hud(draw, width, height, env.metrics(), "Gymnasium Env")
    
    return np.array(img)


def generate_simulation_video(
    config: ProjectConfig,
    agent,
    algorithm: str,
    output_path: str | None = None,
    fps: int = 30,
    frames_per_step: int = 15,
) -> str:
    """Run full simulation and encode high-definition MP4 video using imageio and ffmpeg."""
    if output_path is None:
        temp_dir = tempfile.gettempdir()
        output_path = os.path.join(temp_dir, f"traffic_sim_{algorithm.lower().replace(' ', '_')}.mp4")

    env = TrafficEnvironment(config)
    env.reset(config.simulation.random_seed)

    controller = (
        FixedTimeController(config.signal.maximum_green_time)
        if algorithm == "Fixed Time"
        else None
    )

    lane_count = config.simulation.lane_count
    width, height = 800, 800

    # Collect simulation snapshots
    snapshots = []
    done = False
    while not done:
        action = (
            controller.choose_action(env)
            if controller
            else agent.choose_action(env.get_state(), explore=False)
        )
        result = env.step(action)

        # Snapshot queues & departed
        q_copy = {
            d: [
                {"id": v.vehicle_id, "m": v.movement.value, "l": v.lane_index}
                for v in env.queues[d]
            ]
            for d in DIRECTIONS
        }
        dep_copy = [
            {"id": v.vehicle_id, "d": v.direction, "m": v.movement.value, "l": v.lane_index}
            for v in env.last_departed_vehicles
        ]
        snapshots.append({
            "q": q_copy,
            "dep": dep_copy,
            "phase": env.signal.current_phase.name,
            "active_dir": env.signal.active_direction,
            "metrics": env.metrics(),
        })
        done = result.done

    # Generate frame-by-frame animation
    frames = []
    active_moving_cars = []  # list of dict: {d, m, l, progress, delay}

    for snap_idx, snap in enumerate(snapshots):
        # Add newly departed cars with staggered delays
        for dep_i, v in enumerate(snap["dep"]):
            # Stagger departures: 0.15s offset between vehicles in same step
            stagger_delay = dep_i * (0.2 / max(1, len(snap["dep"])))
            active_moving_cars.append({
                "d": v["d"],
                "m": v["m"],
                "l": v["l"],
                "progress": 0.0,
                "delay": stagger_delay,
            })

        for frame_idx in range(frames_per_step):
            dt = 1.0 / frames_per_step
            img = Image.new("RGB", (width, height), "#0f172a")
            draw = ImageDraw.Draw(img)

            _draw_intersection(draw, width, height, lane_count)
            _draw_lights(draw, width, height, snap["phase"], snap["active_dir"])
            _draw_queues(draw, width, height, snap["q"], lane_count)

            # Advance and draw moving cars
            rem_cars = []
            for car in active_moving_cars:
                if car["delay"] > 0:
                    car["delay"] -= dt
                else:
                    car["progress"] += dt * 0.9  # speed factor
                
                if car["progress"] < 1.0:
                    rem_cars.append(car)
                    if car["progress"] >= 0:
                        x, y, angle = _car_pose(car["d"], car["m"], car["l"], car["progress"], width, height, lane_count)
                        _draw_car(draw, x, y, angle, car["m"])
            active_moving_cars = rem_cars

            _draw_hud(draw, width, height, snap["metrics"], algorithm, snap_idx + 1, len(snapshots))
            frames.append(np.array(img))

    # Write MP4 video with imageio + ffmpeg
    iio.imwrite(output_path, np.stack(frames), fps=fps, codec="libx264")
    return output_path


# ---------------------------------------------------------------------------
# Internal Drawing Utilities
# ---------------------------------------------------------------------------

def _draw_intersection(draw: ImageDraw.ImageDraw, S: int, H: int, lane_count: int):
    C = S / 2
    RW = 180 if lane_count == 2 else 260
    HRW = RW / 2

    # Draw dark asphalt roads
    draw.rectangle([C - HRW, 0, C + HRW, H], fill="#334155")
    draw.rectangle([0, C - HRW, S, C + HRW], fill="#334155")
    draw.rectangle([C - HRW, C - HRW, C + HRW, C + HRW], fill="#1e293b")

    # Lane dividing lines
    total_lanes = 2 if lane_count == 2 else 4
    lw = RW / total_lanes
    start = C - HRW

    for i in range(1, total_lanes):
        off = start + lw * i
        is_center = (i == total_lanes / 2)
        color = "#f59e0b" if is_center else "#94a3b8"

        # North road lines
        draw.line([(off, 0), (off, C - HRW)], fill=color, width=2 if is_center else 1)
        # South road lines
        draw.line([(off, C + HRW), (off, H)], fill=color, width=2 if is_center else 1)
        # West road lines
        draw.line([(0, off), (C - HRW, off)], fill=color, width=2 if is_center else 1)
        # East road lines
        draw.line([(C + HRW, off), (S, off)], fill=color, width=2 if is_center else 1)

    # White Stop lines
    draw.line([(C - HRW, C - HRW), (C + HRW, C - HRW)], fill="#ffffff", width=4)
    draw.line([(C - HRW, C + HRW), (C + HRW, C + HRW)], fill="#ffffff", width=4)
    draw.line([(C - HRW, C - HRW), (C - HRW, C + HRW)], fill="#ffffff", width=4)
    draw.line([(C + HRW, C - HRW), (C + HRW, C + HRW)], fill="#ffffff", width=4)


def _draw_lights(draw: ImageDraw.ImageDraw, S: int, H: int, phase: str, active_dir: str | None):
    C = S / 2
    RW = 260
    HRW = RW / 2

    positions = {
        "north": (C + HRW + 35, C - HRW - 35, "NORTH"),
        "south": (C - HRW - 35, C + HRW + 35, "SOUTH"),
        "east": (C + HRW + 35, C + HRW + 35, "EAST"),
        "west": (C - HRW - 35, C - HRW - 35, "WEST"),
    }

    for dir_name, (x, y, label) in positions.items():
        if phase == "ALL_RED":
            color = "red"
        elif phase == "YELLOW":
            color = "yellow" if dir_name == active_dir else "red"
        else:
            color = "green" if dir_name == active_dir else "red"

        # Light box
        draw.rectangle([x - 14, y - 35, x + 14, y + 35], fill="#0f172a", outline="#475569", width=2)
        
        # Red, Yellow, Green bulbs
        r_col = "#ef4444" if color == "red" else "#450a0a"
        y_col = "#f59e0b" if color == "yellow" else "#451a03"
        g_col = "#22c55e" if color == "green" else "#052e16"

        draw.ellipse([x - 8, y - 28, x + 8, y - 12], fill=r_col)
        draw.ellipse([x - 8, y - 8, x + 8, y + 8], fill=y_col)
        draw.ellipse([x - 8, y + 12, x + 8, y + 28], fill=g_col)


def _draw_queues(draw: ImageDraw.ImageDraw, S: int, H: int, queues: dict, lane_count: int):
    for dir_name in DIRECTIONS:
        q = queues[dir_name]
        lane_counts = {}
        for car in q:
            li = car["l"] if isinstance(car, dict) else car.lane_index
            mov = car["m"] if isinstance(car, dict) else car.movement.value
            lane_counts[li] = lane_counts.get(li, 0)
            
            x, y, angle = _queue_pos(dir_name, li, lane_counts[li], S, H, lane_count)
            _draw_car(draw, x, y, angle, mov)
            lane_counts[li] += 1


def _queue_pos(dir_name: str, li: int, qi: int, S: int, H: int, lane_count: int):
    C = S / 2
    offset = 40 if lane_count == 2 else 45 + li * 38
    spacing = 30
    stop_dist = 145

    angle_map = {"north": math.radians(270), "south": math.radians(90), "east": 0, "west": math.radians(180)}

    if dir_name == "north":
        return C + offset, (C - stop_dist) - qi * spacing, angle_map[dir_name]
    if dir_name == "south":
        return C - offset, (C + stop_dist) + qi * spacing, angle_map[dir_name]
    if dir_name == "east":
        return (C + stop_dist) + qi * spacing, C + offset, angle_map[dir_name]
    return (C - stop_dist) - qi * spacing, C - offset, angle_map[dir_name]


def _car_pose(dir_name: str, mov: str, li: int, t: float, S: int, H: int, lane_count: int):
    C = S / 2
    offset = 40 if lane_count == 2 else 45 + li * 38
    start_dist = 140
    end_dist = 140

    start_map = {
        "north": (C + offset, C - start_dist),
        "south": (C - offset, C + start_dist),
        "east": (C + start_dist, C + offset),
        "west": (C - start_dist, C - offset),
    }
    
    dest_dir = _dest_dir(dir_name, mov)
    end_map = {
        "north": (C - offset, 50),
        "south": (C + offset, H - 50),
        "east": (S - 50, C - offset),
        "west": (50, C + offset),
    }

    p0 = start_map[dir_name]
    p2 = end_map[dest_dir]

    if mov == "straight":
        x = p0[0] + (p2[0] - p0[0]) * t
        y = p0[1] + (p2[1] - p0[1]) * t
        dx = p2[0] - p0[0]
        dy = p2[1] - p0[1]
        angle = math.atan2(dy, dx)
        return x, y, angle

    # Turning Bézier control point
    p1 = _control_point(dir_name, mov, C, lane_count, li)
    u = 1.0 - t
    x = u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0]
    y = u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1]

    # Tangent vector dx, dy for heading angle
    dx = 2 * (1 - t) * (p1[0] - p0[0]) + 2 * t * (p2[0] - p1[0])
    dy = 2 * (1 - t) * (p1[1] - p0[1]) + 2 * t * (p2[1] - p1[1])
    angle = math.atan2(dy, dx)

    return x, y, angle


def _dest_dir(origin: str, mov: str) -> str:
    mapping = {
        "north": {"left": "west", "straight": "south", "right": "east"},
        "south": {"left": "east", "straight": "north", "right": "west"},
        "east": {"left": "north", "straight": "west", "right": "south"},
        "west": {"left": "south", "straight": "east", "right": "north"},
    }
    return mapping[origin][mov]


def _control_point(dir_name: str, mov: str, C: float, lane_count: int, li: int):
    r = 60 if lane_count == 2 else 55 + li * 40
    if dir_name == "north":
        return (C - r, C - r) if mov == "left" else (C + r, C - r)
    if dir_name == "south":
        return (C + r, C + r) if mov == "left" else (C - r, C + r)
    if dir_name == "east":
        return (C + r, C - r) if mov == "left" else (C + r, C + r)
    return (C - r, C + r) if mov == "left" else (C - r, C - r)


def _draw_car(draw: ImageDraw.ImageDraw, x: float, y: float, angle: float, mov: str):
    colors = {"left": "#3b82f6", "straight": "#ef4444", "right": "#22c55e"}
    col = colors.get(mov, "#ef4444")

    w, h = 26, 14
    cos_a, sin_a = math.cos(angle), math.sin(angle)

    def rot(dx, dy):
        return (x + dx * cos_a - dy * sin_a, y + dx * sin_a + dy * cos_a)

    # Car body polygon
    corners = [rot(-w / 2, -h / 2), rot(w / 2, -h / 2), rot(w / 2, h / 2), rot(-w / 2, h / 2)]
    draw.polygon(corners, fill=col, outline="#1e293b")

    # Windshield
    w_corners = [rot(-w * 0.1, -h * 0.35), rot(w * 0.15, -h * 0.35), rot(w * 0.15, h * 0.35), rot(-w * 0.1, h * 0.35)]
    draw.polygon(w_corners, fill="#bae6fd")

    # Headlights
    draw.line([rot(w / 2, -h * 0.35), rot(w / 2, -h * 0.2)], fill="#fef3c7", width=2)
    draw.line([rot(w / 2, h * 0.2), rot(w / 2, h * 0.35)], fill="#fef3c7", width=2)


def _draw_hud(draw: ImageDraw.ImageDraw, S: int, H: int, metrics: dict, alg: str, step: int = 0, total_steps: int = 0):
    # Top banner
    draw.rectangle([0, 0, S, 40], fill="#1e293b")
    draw.line([(0, 40), (S, 40)], fill="#334155", width=1)

    text = f"Alg: {alg}  |  Time: {metrics.get('time', 0)}s  |  Throughput: {metrics.get('throughput', 0)}  |  Avg Wait: {metrics.get('average_waiting_time', 0):.1f}s  |  Reward: {metrics.get('cumulative_reward', 0):.1f}"
    if total_steps > 0:
        text += f"  [{step}/{total_steps}]"
    
    draw.text((16, 12), text, fill="#f8fafc")
