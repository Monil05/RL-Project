import { useEffect, useRef } from "react";
import type { SimulationState, Vehicle } from "../types";
import { CANVAS, movingPose, queuePoint, roadWidth, signalColor } from "./geometry";

interface MovingCar extends Vehicle {
  progress: number;
  delay: number;
}

const COLORS: Record<string, string> = {
  left: "#2563eb",
  straight: "#dc2626",
  right: "#16a34a",
};

export function IntersectionCanvas({ state }: { state: SimulationState | null }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const stateRef = useRef(state);
  const carsRef = useRef<MovingCar[]>([]);
  const seenRef = useRef(0);
  const primedRef = useRef(false);
  stateRef.current = state;

  useEffect(() => {
    let frame = 0;
    let last = performance.now();
    const tick = (now: number) => {
      const dt = Math.min(0.05, (now - last) / 1000);
      last = now;
      const current = stateRef.current;
      if (!current?.ready) {
        primedRef.current = false;
        carsRef.current = [];
        seenRef.current = 0;
      } else if (current.step_index < seenRef.current) {
        carsRef.current = [];
        seenRef.current = 0;
        primedRef.current = false;
      }
      if (current?.ready && !primedRef.current) {
        seenRef.current = current.step_index;
        primedRef.current = true;
      } else if (current?.ready) {
        current.departure_log.forEach((event) => {
          if (event.step_index <= seenRef.current) return;
          event.departed.forEach((vehicle, index) => {
            carsRef.current.push({ ...vehicle, progress: 0, delay: index * 0.12 });
          });
          seenRef.current = Math.max(seenRef.current, event.step_index);
        });
      }
      carsRef.current = carsRef.current
        .map((car) => {
          if (car.delay > 0) return { ...car, delay: car.delay - dt };
          return { ...car, progress: Math.min(1, car.progress + dt * 1.4) };
        })
        .filter((car) => car.progress < 1);
      paint(canvasRef.current, current, carsRef.current);
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

function paint(canvas: HTMLCanvasElement | null, state: SimulationState | null, cars: MovingCar[]) {
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
  const left = CANVAS / 2 - width / 2;
  context.clearRect(0, 0, CANVAS, CANVAS);
  context.fillStyle = "#e8eef5";
  context.fillRect(0, 0, CANVAS, CANVAS);
  context.fillStyle = "#334155";
  context.fillRect(left, 0, width, CANVAS);
  context.fillRect(0, left, CANVAS, width);
  context.fillStyle = "#1e293b";
  context.fillRect(left, left, width, width);
  drawLanes(context, laneCount, width);
  drawStopLines(context, width);
  drawLights(context, state, width);
  drawQueues(context, state);
  cars.forEach((car) => {
    if (car.delay > 0) return;
    const pose = movingPose(car.direction, car.movement, car.lane_index, car.progress, laneCount);
    drawCar(context, pose.x, pose.y, pose.angle, car.movement, false);
  });
  if (!state?.ready) {
    context.fillStyle = "rgba(15, 23, 42, 0.55)";
    context.fillRect(0, 0, CANVAS, CANVAS);
    context.fillStyle = "#f8fafc";
    context.font = "600 18px Segoe UI, sans-serif";
    context.textAlign = "center";
    context.fillText("Simulation not loaded", CANVAS / 2, CANVAS / 2);
  }
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

function drawLights(context: CanvasRenderingContext2D, state: SimulationState | null, width: number) {
  const half = width / 2;
  const center = CANVAS / 2;
  const positions: Record<string, [number, number, string]> = {
    north: [center + half + 28, center - half - 28, "N"],
    south: [center - half - 28, center + half + 28, "S"],
    east: [center + half + 28, center + half + 28, "E"],
    west: [center - half - 28, center - half - 28, "W"],
  };
  Object.entries(positions).forEach(([direction, [x, y, label]]) => {
    const color = signalColor(state?.signal?.phase ?? "ALL_RED", state?.signal?.active_direction ?? null, direction);
    const bulbs = {
      red: ["#ef4444", "#450a0a", "#450a0a"],
      yellow: ["#450a0a", "#f59e0b", "#052e16"],
      green: ["#450a0a", "#451a03", "#22c55e"],
    }[color];
    roundRect(context, x - 14, y - 34, 28, 68, 6);
    context.fillStyle = "#0f172a";
    context.fill();
    bulbs.forEach((fill, index) => {
      context.fillStyle = fill;
      context.beginPath();
      context.arc(x, y - 20 + index * 20, 6, 0, Math.PI * 2);
      context.fill();
    });
    context.fillStyle = "#334155";
    context.font = "700 12px Segoe UI, sans-serif";
    context.textAlign = "center";
    context.fillText(label, x, y + 48);
  });
}

function drawQueues(context: CanvasRenderingContext2D, state: SimulationState | null) {
  if (!state?.ready) return;
  (["north", "south", "east", "west"] as const).forEach((direction) => {
    const counts: Record<number, number> = {};
    state.queues[direction]?.forEach((vehicle) => {
      const lane = vehicle.lane_index;
      const index = counts[lane] ?? 0;
      counts[lane] = index + 1;
      const [x, y] = queuePoint(direction, lane, index, state.lane_count);
      const angle = { north: -Math.PI / 2, south: Math.PI / 2, east: 0, west: Math.PI }[direction];
      drawCar(context, x, y, angle, vehicle.movement, true);
    });
  });
}

function drawCar(context: CanvasRenderingContext2D, x: number, y: number, angle: number, movement: string, queued: boolean) {
  context.save();
  context.translate(x, y);
  context.rotate(angle);
  context.globalAlpha = queued ? 0.85 : 1;
  roundRect(context, -13, -6, 26, 12, 3);
  context.fillStyle = COLORS[movement] ?? COLORS.straight;
  context.fill();
  context.strokeStyle = "#0f172a";
  context.lineWidth = 0.8;
  context.stroke();
  roundRect(context, -4, -4, 8, 8, 1.5);
  context.fillStyle = "rgba(186, 230, 253, 0.9)";
  context.fill();
  context.fillStyle = "#fef3c7";
  context.fillRect(10, -5, 2, 2);
  context.fillRect(10, 3, 2, 2);
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
