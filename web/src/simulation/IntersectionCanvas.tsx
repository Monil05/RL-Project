import { useEffect, useRef } from "react";
import type { SimulationState, Vehicle } from "../types";
import { CANVAS, movingPose, queuePose, roadWidth, signalColor } from "./geometry";
import { stepLamps, type LampPhase, type LampPlayback } from "./signalPlayback";

const DIRECTIONS = ["north", "south", "east", "west"] as const;

interface Queues {
  [direction: string]: Vehicle[];
}

interface Snap {
  step: number;
  queues: Queues;
}

const COLORS: Record<string, { body: string; roof: string }> = {
  left: { body: "#2563eb", roof: "#1e3a8a" },
  straight: { body: "#dc2626", roof: "#7f1d1d" },
  right: { body: "#16a34a", roof: "#14532d" },
};

const DIM = { red: "#3f1d1d", yellow: "#3f3514", green: "#14301f" };
const LIT = { red: "#ef4444", yellow: "#facc15", green: "#22c55e" };
const INITIAL_LAMPS: LampPlayback = {
  shown: { phase: "ALL_RED", active: null },
  holdDirection: null,
  holdUntil: 0,
  pending: null,
};

export function IntersectionCanvas({
  state,
  onLamp,
}: {
  state: SimulationState | null;
  onLamp?: (lamp: LampPhase | null) => void;
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  const onLampRef = useRef(onLamp);
  const visualStep = useRef(0);
  const fromSnap = useRef<Snap | null>(null);
  const toSnap = useRef<Snap | null>(null);
  const playback = useRef<LampPlayback>(INITIAL_LAMPS);
  const primed = useRef(false);
  const reported = useRef("");
  stateRef.current = state;
  onLampRef.current = onLamp;

  useEffect(() => {
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const current = stateRef.current;
      if (!current?.ready) {
        visualStep.current = 0;
        fromSnap.current = null;
        toSnap.current = null;
        primed.current = false;
        playback.current = INITIAL_LAMPS;
      } else if (toSnap.current && current.step_index < toSnap.current.step) {
        visualStep.current = current.step_index;
        const snap = { step: current.step_index, queues: cloneQueues(current.queues) };
        fromSnap.current = snap;
        toSnap.current = snap;
        primed.current = false;
        playback.current = INITIAL_LAMPS;
      } else if (!toSnap.current) {
        const snap = { step: current.step_index, queues: cloneQueues(current.queues) };
        fromSnap.current = snap;
        toSnap.current = snap;
        visualStep.current = current.step_index;
      } else if (current.step_index > toSnap.current.step) {
        fromSnap.current = toSnap.current;
        toSnap.current = { step: current.step_index, queues: cloneQueues(current.queues) };
      }
      const duration = Math.max(0.05, 0.25 / Math.max(current?.speed ?? 1, 0.25));
      if (current?.ready && visualStep.current < current.step_index) {
        visualStep.current = Math.min(current.step_index, visualStep.current + dt / duration);
      }
      const lamp = shownLamp(current, visualStep.current, now, playback, primed);
      reportLamp(lamp, reported, onLampRef.current);
      paint(canvasRef.current, current, visualStep.current, fromSnap.current, toSnap.current, lamp);
      frame = requestAnimationFrame(tick);
    };
    frame = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(frame);
  }, []);

  return (
    <canvas
      ref={canvasRef}
      width={CANVAS}
      height={CANVAS}
      role="img"
      aria-label="Four-way intersection visualization"
      className="h-auto w-full rounded-xl bg-slate-200"
    />
  );
}

function paint(
  canvas: HTMLCanvasElement | null,
  state: SimulationState | null,
  visualStep: number,
  fromSnap: Snap | null,
  toSnap: Snap | null,
  lamp: LampPhase | null,
) {
  if (!canvas) return;
  let context: CanvasRenderingContext2D | null = null;
  try {
    context = canvas.getContext("2d");
  } catch {
    return;
  }
  if (!context) return;
  const laneCount = state?.lane_count ?? 2;
  const width = roadWidth(laneCount);
  context.clearRect(0, 0, CANVAS, CANVAS);
  drawRoad(context, width);
  drawLanes(context, laneCount, width);
  drawCrosswalks(context, width);
  drawStopLines(context, width);
  const phase = lamp ?? { phase: "ALL_RED", active: null };
  drawLights(context, phase.phase, phase.active, width);
  if (state?.ready && fromSnap && toSnap) {
    const hidden: Record<string, number> = { north: 0, south: 0, east: 0, west: 0 };
    carsBetween(fromSnap, toSnap, state, visualStep, laneCount).forEach((car) => {
      if (car.x < 22 || car.y < 22 || car.x > CANVAS - 22 || car.y > CANVAS - 22) {
        hidden[car.direction] += 1;
        return;
      }
      drawCar(context, car.x, car.y, car.angle, car.movement, car.queued);
    });
    drawBacklog(context, hidden, width);
  }
  if (!state?.ready) {
    context.fillStyle = "rgba(15, 23, 42, 0.55)";
    context.fillRect(0, 0, CANVAS, CANVAS);
    context.fillStyle = "#f8fafc";
    context.font = "600 18px Segoe UI, sans-serif";
    context.textAlign = "center";
    context.fillText("Simulation not loaded", CANVAS / 2, CANVAS / 2);
  }
}

function carsBetween(fromSnap: Snap, toSnap: Snap, state: SimulationState, visualStep: number, laneCount: number) {
  const span = Math.max(1, toSnap.step - fromSnap.step);
  const mix = Math.min(1, Math.max(0, (visualStep - fromSnap.step) / span));
  const seen = new Set<number>();
  const drawn: { x: number; y: number; angle: number; movement: string; queued: boolean; direction: string }[] = [];

  for (const direction of DIRECTIONS) {
    const counts: Record<number, number> = {};
    for (const vehicle of toSnap.queues[direction] ?? []) {
      const lane = vehicle.lane_index;
      const index = counts[lane] ?? 0;
      counts[lane] = index + 1;
      seen.add(vehicle.id);
      const target = queuePose(direction, lane, index, laneCount);
      const previous = slotOf(fromSnap.queues, vehicle.id, laneCount);
      const origin = previous?.pose ?? queuePose(direction, lane, index + 1, laneCount);
      drawn.push({
        x: origin.x + (target.x - origin.x) * mix,
        y: origin.y + (target.y - origin.y) * mix,
        angle: lerpAngle(origin.angle, target.angle, mix),
        movement: vehicle.movement,
        queued: true,
        direction,
      });
    }
  }

  for (const direction of DIRECTIONS) {
    for (const vehicle of fromSnap.queues[direction] ?? []) {
      if (seen.has(vehicle.id)) continue;
      const leftAt = departureStep(state, vehicle.id) ?? toSnap.step;
      const progress = Math.min(1, Math.max(0, visualStep - (leftAt - 1)));
      if (progress >= 1) continue;
      const previous = slotOf(fromSnap.queues, vehicle.id, laneCount);
      const pose = movingPose(vehicle.direction, vehicle.movement, vehicle.lane_index, progress, laneCount, previous?.pose.angle);
      drawn.push({ ...pose, movement: vehicle.movement, queued: false, direction: vehicle.direction });
    }
  }
  return drawn;
}

function slotOf(queues: Queues, id: number, laneCount: number) {
  for (const direction of DIRECTIONS) {
    const counts: Record<number, number> = {};
    for (const vehicle of queues[direction] ?? []) {
      const lane = vehicle.lane_index;
      const index = counts[lane] ?? 0;
      if (vehicle.id === id) {
        return { pose: queuePose(direction, lane, index, laneCount) };
      }
      counts[lane] = index + 1;
    }
  }
  return null;
}

function departureStep(state: SimulationState, id: number): number | null {
  for (const event of state.departure_log ?? []) {
    if (event.departed.some((vehicle) => vehicle.id === id)) return event.step_index;
  }
  return null;
}

function shownLamp(
  state: SimulationState | null,
  visualStep: number,
  now: number,
  playback: { current: LampPlayback },
  primed: { current: boolean },
): LampPhase | null {
  if (!state?.ready) return null;
  const server = phaseAt(state, visualStep);
  if (!primed.current) {
    playback.current = { shown: server, holdDirection: null, holdUntil: 0, pending: null };
    primed.current = true;
    return server;
  }
  playback.current = stepLamps(playback.current, server, now);
  return playback.current.shown;
}

function reportLamp(
  lamp: LampPhase | null,
  reported: { current: string },
  onLamp: ((lamp: LampPhase | null) => void) | undefined,
) {
  const key = lamp ? `${lamp.phase}:${lamp.active ?? ""}` : "";
  if (reported.current === key) return;
  reported.current = key;
  onLamp?.(lamp);
}

function phaseAt(state: SimulationState | null, visualStep: number): LampPhase {
  let phase = state?.signal?.phase ?? "ALL_RED";
  let active = state?.signal?.active_direction ?? null;
  const step = Math.ceil(visualStep);
  for (const entry of state?.phase_log ?? []) {
    if (entry.step_index <= step) {
      phase = entry.phase;
      active = entry.active_direction;
    }
  }
  return { phase, active };
}

function cloneQueues(queues: SimulationState["queues"]): Queues {
  const copy: Queues = {};
  for (const direction of DIRECTIONS) copy[direction] = (queues?.[direction] ?? []).map((vehicle) => ({ ...vehicle }));
  return copy;
}

function lerpAngle(from: number, to: number, mix: number): number {
  let delta = to - from;
  while (delta > Math.PI) delta -= Math.PI * 2;
  while (delta < -Math.PI) delta += Math.PI * 2;
  return from + delta * mix;
}

function drawRoad(context: CanvasRenderingContext2D, width: number) {
  const left = CANVAS / 2 - width / 2;
  context.fillStyle = "#d7e0ea";
  context.fillRect(0, 0, CANVAS, CANVAS);
  context.fillStyle = "#c3cedb";
  context.fillRect(14, 14, CANVAS - 28, CANVAS - 28);
  context.fillStyle = "#3d4b63";
  context.fillRect(left, 0, width, CANVAS);
  context.fillRect(0, left, CANVAS, width);
  context.strokeStyle = "rgba(226, 232, 240, 0.55)";
  context.lineWidth = 2;
  context.strokeRect(left + 1, 0, width - 2, CANVAS);
  context.beginPath();
  context.moveTo(0, left + 1);
  context.lineTo(CANVAS, left + 1);
  context.moveTo(0, left + width - 1);
  context.lineTo(CANVAS, left + width - 1);
  context.stroke();
}

function drawCrosswalks(context: CanvasRenderingContext2D, width: number) {
  const center = CANVAS / 2;
  const half = width / 2;
  const outer = half + 16;
  const inner = half + 4;
  context.fillStyle = "rgba(255,255,255,0.88)";
  stripeBand(context, center - half + 8, center - outer, width - 16, outer - inner, true);
  stripeBand(context, center - half + 8, center + inner, width - 16, outer - inner, true);
  stripeBand(context, center - outer, center - half + 8, outer - inner, width - 16, false);
  stripeBand(context, center + inner, center - half + 8, outer - inner, width - 16, false);
}

function stripeBand(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  across: boolean,
) {
  const count = 6;
  const gap = 5;
  if (across) {
    const thickness = (width - gap * (count - 1)) / count;
    for (let index = 0; index < count; index += 1) {
      context.fillRect(x + index * (thickness + gap), y, thickness, height);
    }
    return;
  }
  const thickness = (height - gap * (count - 1)) / count;
  for (let index = 0; index < count; index += 1) {
    context.fillRect(x, y + index * (thickness + gap), width, thickness);
  }
}

function drawBacklog(context: CanvasRenderingContext2D, hidden: Record<string, number>, width: number) {
  const center = CANVAS / 2;
  const half = width / 2;
  const marks: Record<string, [number, number]> = {
    north: [center + half * 0.5, 28],
    south: [center - half * 0.5, CANVAS - 18],
    east: [CANVAS - 36, center + half * 0.5],
    west: [36, center - half * 0.5],
  };
  context.font = "700 12px Segoe UI, sans-serif";
  context.textAlign = "center";
  context.textBaseline = "middle";
  for (const [direction, count] of Object.entries(hidden)) {
    if (count < 1) continue;
    const [x, y] = marks[direction];
    const label = `+${count}`;
    const box = context.measureText(label).width + 14;
    roundRect(context, x - box / 2, y - 10, box, 20, 10);
    context.fillStyle = "#0f172a";
    context.fill();
    context.fillStyle = "#f8fafc";
    context.fillText(label, x, y + 1);
  }
  context.textBaseline = "alphabetic";
}

function drawLanes(context: CanvasRenderingContext2D, laneCount: number, width: number) {
  const total = laneCount === 2 ? 2 : 4;
  const lane = width / total;
  const start = CANVAS / 2 - width / 2;
  const edge = start;
  const far = CANVAS / 2 + width / 2;
  for (let index = 1; index < total; index += 1) {
    const offset = start + lane * index;
    const center = index === total / 2;
    context.strokeStyle = center ? "#f59e0b" : "#cbd5e1";
    context.lineWidth = center ? 2.5 : 1.5;
    context.setLineDash(center ? [] : [8, 10]);
    context.beginPath();
    context.moveTo(offset, 0);
    context.lineTo(offset, edge);
    context.stroke();
    context.beginPath();
    context.moveTo(offset, far);
    context.lineTo(offset, CANVAS);
    context.stroke();
    context.beginPath();
    context.moveTo(0, offset);
    context.lineTo(edge, offset);
    context.stroke();
    context.beginPath();
    context.moveTo(far, offset);
    context.lineTo(CANVAS, offset);
    context.stroke();
  }
  context.setLineDash([]);
}

function drawStopLines(context: CanvasRenderingContext2D, width: number) {
  const edge = CANVAS / 2 - width / 2;
  const far = CANVAS / 2 + width / 2;
  context.strokeStyle = "#ffffff";
  context.lineWidth = 4;
  [
    [edge, edge, far, edge],
    [edge, far, far, far],
    [edge, edge, edge, far],
    [far, edge, far, far],
  ].forEach(([x1, y1, x2, y2]) => {
    context.beginPath();
    context.moveTo(x1, y1);
    context.lineTo(x2, y2);
    context.stroke();
  });
}

function drawLights(context: CanvasRenderingContext2D, phase: string, active: string | null, width: number) {
  const half = width / 2;
  const center = CANVAS / 2;
  const positions: Record<string, [number, number, string]> = {
    north: [center + half + 42, center - half - 46, "N"],
    south: [center - half - 42, center + half + 46, "S"],
    east: [center + half + 42, center + half + 46, "E"],
    west: [center - half - 42, center - half - 46, "W"],
  };
  Object.entries(positions).forEach(([direction, [x, y, label]]) => {
    const color = signalColor(phase, active, direction);
    roundRect(context, x - 16, y - 40, 32, 80, 8);
    context.fillStyle = "#0f172a";
    context.fill();
    context.lineWidth = 2;
    context.strokeStyle = "#475569";
    context.stroke();
    (["red", "yellow", "green"] as const).forEach((lamp, index) => {
      const on = color === lamp;
      const cy = y - 24 + index * 24;
      context.beginPath();
      context.fillStyle = on ? LIT[lamp] : DIM[lamp];
      context.shadowColor = on ? LIT[lamp] : "transparent";
      context.shadowBlur = on ? 18 : 0;
      context.arc(x, cy, 9, 0, Math.PI * 2);
      context.fill();
      if (on) {
        context.beginPath();
        context.fillStyle = "rgba(255,255,255,0.9)";
        context.arc(x, cy, 3, 0, Math.PI * 2);
        context.fill();
      }
    });
    context.shadowBlur = 0;
    context.fillStyle = "#334155";
    context.font = "700 13px Segoe UI, sans-serif";
    context.textAlign = "center";
    context.fillText(label, x, y + 56);
  });
}

function drawCar(context: CanvasRenderingContext2D, x: number, y: number, angle: number, movement: string, queued: boolean) {
  const palette = COLORS[movement] ?? COLORS.straight;
  context.save();
  context.translate(x, y);
  context.rotate(angle);
  context.fillStyle = "rgba(15, 23, 42, 0.28)";
  roundRect(context, -11, -3, 26, 12, 4);
  context.fill();
  context.fillStyle = "#0f172a";
  context.fillRect(-8, -8, 5, 3);
  context.fillRect(3, -8, 5, 3);
  context.fillRect(-8, 5, 5, 3);
  context.fillRect(3, 5, 5, 3);
  roundRect(context, -13, -6.5, 27, 13, 4);
  context.fillStyle = palette.body;
  context.fill();
  context.strokeStyle = "rgba(15, 23, 42, 0.45)";
  context.lineWidth = 1;
  context.stroke();
  roundRect(context, -4, -5, 10, 10, 2);
  context.fillStyle = palette.roof;
  context.fill();
  context.fillStyle = "rgba(224, 242, 254, 0.95)";
  context.fillRect(2, -4, 5, 8);
  context.fillStyle = queued ? "#fb7185" : "#fef9c3";
  context.fillRect(queued ? -14 : 12, -5, 2.5, 2.5);
  context.fillRect(queued ? -14 : 12, 2.5, 2.5, 2.5);
  context.restore();
}

function roundRect(context: CanvasRenderingContext2D, x: number, y: number, width: number, height: number, radius: number) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.arcTo(x + width, y, x + width, y + height, radius);
  context.arcTo(x + width, y + height, x, y + height, radius);
  context.arcTo(x, y + height, x, y, radius);
  context.arcTo(x, y, x + width, y, radius);
  context.closePath();
}
