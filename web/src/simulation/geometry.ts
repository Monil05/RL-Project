export const CANVAS = 760;
const CENTER = CANVAS / 2;

export function roadWidth(laneCount: number): number {
  return laneCount === 2 ? 170 : 250;
}

export function approach(direction: string, laneIndex: number, laneCount: number): [number, number] {
  const offset = laneCount === 2 ? 36 : 42 + laneIndex * 34;
  const stop = laneCount === 2 ? 120 : 150;
  if (direction === "north") return [CENTER + offset, CENTER - stop];
  if (direction === "south") return [CENTER - offset, CENTER + stop];
  if (direction === "east") return [CENTER + stop, CENTER + offset];
  return [CENTER - stop, CENTER - offset];
}

export function queuePoint(direction: string, laneIndex: number, queueIndex: number, laneCount: number): [number, number] {
  const [x, y] = approach(direction, laneIndex, laneCount);
  const spacing = 28;
  if (direction === "north") return [x, y - spacing * queueIndex];
  if (direction === "south") return [x, y + spacing * queueIndex];
  if (direction === "east") return [x + spacing * queueIndex, y];
  return [x - spacing * queueIndex, y];
}

function destinationDirection(origin: string, movement: string): string {
  const table: Record<string, Record<string, string>> = {
    north: { left: "west", straight: "south", right: "east" },
    south: { left: "east", straight: "north", right: "west" },
    east: { left: "north", straight: "west", right: "south" },
    west: { left: "south", straight: "east", right: "north" },
  };
  return table[origin][movement];
}

function exitPoint(direction: string, laneIndex: number, laneCount: number): [number, number] {
  const offset = laneCount === 2 ? 36 : 42 + laneIndex * 34;
  if (direction === "north") return [CENTER - offset, 40];
  if (direction === "south") return [CENTER + offset, CANVAS - 40];
  if (direction === "east") return [CANVAS - 40, CENTER - offset];
  return [40, CENTER + offset];
}

function controlPoint(direction: string, movement: string, laneIndex: number, laneCount: number): [number, number] {
  const radius = laneCount === 2 ? 58 : 50 + laneIndex * 36;
  if (direction === "north") return movement === "left" ? [CENTER - radius, CENTER - radius] : [CENTER + radius, CENTER - radius];
  if (direction === "south") return movement === "left" ? [CENTER + radius, CENTER + radius] : [CENTER - radius, CENTER + radius];
  if (direction === "east") return movement === "left" ? [CENTER + radius, CENTER - radius] : [CENTER + radius, CENTER + radius];
  return movement === "left" ? [CENTER - radius, CENTER + radius] : [CENTER - radius, CENTER - radius];
}

export function movingPose(
  direction: string,
  movement: string,
  laneIndex: number,
  progress: number,
  laneCount: number,
): { x: number; y: number; angle: number } {
  const start = approach(direction, laneIndex, laneCount);
  const end = exitPoint(destinationDirection(direction, movement), laneIndex, laneCount);
  if (movement === "straight") {
    const x = start[0] + (end[0] - start[0]) * progress;
    const y = start[1] + (end[1] - start[1]) * progress;
    return { x, y, angle: Math.atan2(end[1] - start[1], end[0] - start[0]) };
  }
  const control = controlPoint(direction, movement, laneIndex, laneCount);
  const inverse = 1 - progress;
  const x = inverse * inverse * start[0] + 2 * inverse * progress * control[0] + progress * progress * end[0];
  const y = inverse * inverse * start[1] + 2 * inverse * progress * control[1] + progress * progress * end[1];
  const dx = 2 * inverse * (control[0] - start[0]) + 2 * progress * (end[0] - control[0]);
  const dy = 2 * inverse * (control[1] - start[1]) + 2 * progress * (end[1] - control[1]);
  return { x, y, angle: Math.atan2(dy, dx) };
}

export function signalColor(phase: string, active: string | null, direction: string): "red" | "yellow" | "green" {
  if (phase === "ALL_RED") return "red";
  if (phase === "YELLOW") return direction === active ? "yellow" : "red";
  return direction === active ? "green" : "red";
}
