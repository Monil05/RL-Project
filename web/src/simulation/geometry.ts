export const CANVAS = 760;
const CENTER = CANVAS / 2;
const EDGE = 36;
const QUEUE_GAP = 28;

const TRAVEL: Record<string, [number, number]> = {
  north: [0, 1],
  south: [0, -1],
  east: [-1, 0],
  west: [1, 0],
};

const HEADING: Record<string, number> = {
  north: Math.PI / 2,
  south: -Math.PI / 2,
  east: Math.PI,
  west: 0,
};

export function roadWidth(laneCount: number): number {
  return laneCount === 2 ? 170 : 250;
}

export function approachHeading(direction: string): number {
  return HEADING[direction] ?? 0;
}

function lanesPerDirection(laneCount: number): number {
  return laneCount === 2 ? 1 : 2;
}

function laneWidth(laneCount: number): number {
  return roadWidth(laneCount) / (lanesPerDirection(laneCount) * 2);
}

function clampLane(laneIndex: number, laneCount: number): number {
  return Math.min(Math.max(0, laneIndex), lanesPerDirection(laneCount) - 1);
}

/** Distance from the road centerline to an incoming lane. Lane 0 is the inner lane. */
function lateralOffset(laneIndex: number, laneCount: number): number {
  return laneWidth(laneCount) * (clampLane(laneIndex, laneCount) + 0.5);
}

function stopDistance(laneCount: number): number {
  return roadWidth(laneCount) / 2 + 18;
}

export function stopPoint(direction: string, laneIndex: number, laneCount: number): [number, number] {
  const offset = lateralOffset(laneIndex, laneCount);
  const stop = stopDistance(laneCount);
  if (direction === "north") return [CENTER + offset, CENTER - stop];
  if (direction === "south") return [CENTER - offset, CENTER + stop];
  if (direction === "east") return [CENTER + stop, CENTER + offset];
  return [CENTER - stop, CENTER - offset];
}

export function approach(direction: string, laneIndex: number, laneCount: number): [number, number] {
  return stopPoint(direction, laneIndex, laneCount);
}

export function queuePoint(direction: string, laneIndex: number, queueIndex: number, laneCount: number): [number, number] {
  const pose = queuePose(direction, laneIndex, queueIndex, laneCount);
  return [pose.x, pose.y];
}

export function queuePose(
  direction: string,
  laneIndex: number,
  queueIndex: number,
  laneCount: number,
): { x: number; y: number; angle: number } {
  const [x, y] = stopPoint(direction, laneIndex, laneCount);
  const [tx, ty] = TRAVEL[direction] ?? [0, 1];
  return {
    x: x - tx * QUEUE_GAP * queueIndex,
    y: y - ty * QUEUE_GAP * queueIndex,
    angle: approachHeading(direction),
  };
}

function destinationDirection(origin: string, movement: string): string {
  const table: Record<string, Record<string, string>> = {
    north: { left: "west", straight: "south", right: "east" },
    south: { left: "east", straight: "north", right: "west" },
    east: { left: "north", straight: "west", right: "south" },
    west: { left: "south", straight: "east", right: "north" },
  };
  return table[origin]?.[movement] ?? "south";
}

function approachForHeading(heading: string): string {
  return { south: "north", north: "south", west: "east", east: "west" }[heading] ?? "north";
}

function straightEnd(direction: string, laneIndex: number, laneCount: number): [number, number] {
  const [x, y] = stopPoint(direction, laneIndex, laneCount);
  if (direction === "north") return [x, CANVAS - EDGE];
  if (direction === "south") return [x, EDGE];
  if (direction === "east") return [EDGE, y];
  return [CANVAS - EDGE, y];
}

function junctionPoint(
  direction: string,
  laneIndex: number,
  laneCount: number,
  side: "near" | "far",
): [number, number] {
  const half = roadWidth(laneCount) / 2;
  const [x, y] = stopPoint(direction, laneIndex, laneCount);
  const near = side === "near";
  if (direction === "north") return [x, near ? CENTER - half : CENTER + half];
  if (direction === "south") return [x, near ? CENTER + half : CENTER - half];
  if (direction === "east") return [near ? CENTER + half : CENTER - half, y];
  return [near ? CENTER - half : CENTER + half, y];
}

export function movingPose(
  direction: string,
  movement: string,
  laneIndex: number,
  progress: number,
  laneCount: number,
  previousAngle = approachHeading(direction),
): { x: number; y: number; angle: number } {
  const start = stopPoint(direction, laneIndex, laneCount);
  const heading = destinationDirection(direction, movement);
  const exitApproach = approachForHeading(heading);
  const end = straightEnd(exitApproach, laneIndex, laneCount);
  const clamped = Math.min(1, Math.max(0, progress));
  if (movement === "straight") {
    return {
      x: start[0] + (end[0] - start[0]) * clamped,
      y: start[1] + (end[1] - start[1]) * clamped,
      angle: approachHeading(direction),
    };
  }
  const entry = junctionPoint(direction, laneIndex, laneCount, "near");
  const leave = junctionPoint(exitApproach, laneIndex, laneCount, "far");
  const [tx, ty] = TRAVEL[direction] ?? [0, 1];
  const [ex, ey] = TRAVEL[exitApproach] ?? [0, 1];
  if (clamped < 0.2) {
    const mix = clamped / 0.2;
    return {
      x: start[0] + (entry[0] - start[0]) * mix,
      y: start[1] + (entry[1] - start[1]) * mix,
      angle: approachHeading(direction),
    };
  }
  if (clamped > 0.8) {
    const mix = (clamped - 0.8) / 0.2;
    return {
      x: leave[0] + (end[0] - leave[0]) * mix,
      y: leave[1] + (end[1] - leave[1]) * mix,
      angle: approachHeading(exitApproach),
    };
  }
  const handle = (roadWidth(laneCount) / 2) * 0.65;
  const curve = cubic(
    entry,
    [entry[0] + tx * handle, entry[1] + ty * handle],
    [leave[0] - ex * handle, leave[1] - ey * handle],
    leave,
    (clamped - 0.2) / 0.6,
  );
  const length = Math.hypot(curve.dx, curve.dy);
  return {
    x: curve.x,
    y: curve.y,
    angle: length < 0.001 ? previousAngle : Math.atan2(curve.dy, curve.dx),
  };
}
function cubic(
  p0: [number, number],
  p1: [number, number],
  p2: [number, number],
  p3: [number, number],
  t: number,
): { x: number; y: number; dx: number; dy: number } {
  const u = 1 - t;
  const x = u * u * u * p0[0] + 3 * u * u * t * p1[0] + 3 * u * t * t * p2[0] + t * t * t * p3[0];
  const y = u * u * u * p0[1] + 3 * u * u * t * p1[1] + 3 * u * t * t * p2[1] + t * t * t * p3[1];
  const dx = 3 * u * u * (p1[0] - p0[0]) + 6 * u * t * (p2[0] - p1[0]) + 3 * t * t * (p3[0] - p2[0]);
  const dy = 3 * u * u * (p1[1] - p0[1]) + 6 * u * t * (p2[1] - p1[1]) + 3 * t * t * (p3[1] - p2[1]);
  return { x, y, dx, dy };
}

export function signalColor(phase: string, active: string | null, direction: string): "red" | "yellow" | "green" {
  if (phase === "ALL_RED" || phase === "") return "red";
  if (phase === "YELLOW") return direction === active ? "yellow" : "red";
  return direction === active ? "green" : "red";
}
