import { describe, expect, it } from "vitest";
import { movingPose, queuePose, signalColor } from "../simulation/geometry";

function angleClose(actual: number, expected: number): boolean {
  const delta = Math.atan2(Math.sin(actual - expected), Math.cos(actual - expected));
  return Math.abs(delta) < 0.2;
}

describe("lane geometry", () => {
  it("faces a northbound queue toward the intersection", () => {
    const pose = queuePose("north", 0, 0, 2);
    expect(angleClose(pose.angle, Math.PI / 2)).toBe(true);
  });

  it("keeps two cars in different slots of the same lane", () => {
    const first = queuePose("north", 0, 0, 2);
    const second = queuePose("north", 0, 1, 2);
    expect(first.x).toBeCloseTo(second.x, 5);
    expect(second.y).toBeLessThan(first.y - 20);
  });

  it("starts a left turn along the approach and ends along the exit lane", () => {
    const start = movingPose("north", "left", 0, 0, 2);
    const justAfter = movingPose("north", "left", 0, 0.05, 2);
    const justBefore = movingPose("north", "left", 0, 0.95, 2);
    const end = movingPose("north", "left", 0, 1, 2);
    expect(angleClose(start.angle, Math.PI / 2)).toBe(true);
    expect(angleClose(justAfter.angle, Math.PI / 2)).toBe(true);
    expect(angleClose(justBefore.angle, Math.PI)).toBe(true);
    expect(angleClose(end.angle, Math.PI)).toBe(true);
    expect(end.x).toBeLessThan(start.x);
  });
});

describe("signal lamps", () => {
  it("lights yellow only on the active approach", () => {
    expect(signalColor("YELLOW", "north", "north")).toBe("yellow");
    expect(signalColor("YELLOW", "north", "south")).toBe("red");
    expect(signalColor("YELLOW", "north", "east")).toBe("red");
    expect(signalColor("YELLOW", "north", "west")).toBe("red");
  });

  it("lights green only on the active approach and red everywhere during all-red", () => {
    expect(signalColor("NORTH_GREEN", "north", "north")).toBe("green");
    expect(signalColor("NORTH_GREEN", "north", "east")).toBe("red");
    for (const direction of ["north", "south", "east", "west"]) {
      expect(signalColor("ALL_RED", null, direction)).toBe("red");
    }
  });
});
