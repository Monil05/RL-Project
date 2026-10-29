import { describe, expect, it } from "vitest";
import { signalColor } from "./geometry";
import { stepLamps, type LampPlayback, type LampPhase } from "./signalPlayback";

function play(shown: LampPhase): LampPlayback {
  return { shown, holdDirection: null, holdUntil: 0, pending: null };
}

describe("signal playback", () => {
  it("keeps the current green when the approach does not change", () => {
    const west: LampPhase = { phase: "WEST_GREEN", active: "west" };
    const next = stepLamps(play(west), west, 0);
    expect(next.shown).toEqual(west);
    expect(signalColor(next.shown.phase, next.shown.active, "west")).toBe("green");
  });

  it("lights yellow on the approach that is giving way before the next green", () => {
    const started = stepLamps(
      play({ phase: "WEST_GREEN", active: "west" }),
      { phase: "NORTH_GREEN", active: "north" },
      1000,
    );
    expect(started.shown).toEqual({ phase: "YELLOW", active: "west" });
    expect(signalColor(started.shown.phase, started.shown.active, "west")).toBe("yellow");
    expect(signalColor(started.shown.phase, started.shown.active, "north")).toBe("red");
    expect(signalColor(started.shown.phase, started.shown.active, "south")).toBe("red");
    expect(signalColor(started.shown.phase, started.shown.active, "east")).toBe("red");

    const held = stepLamps(started, { phase: "NORTH_GREEN", active: "north" }, 1500);
    expect(held.shown.phase).toBe("YELLOW");

    const released = stepLamps(held, { phase: "NORTH_GREEN", active: "north" }, 2000);
    expect(released.shown).toEqual({ phase: "NORTH_GREEN", active: "north" });
    expect(signalColor(released.shown.phase, released.shown.active, "north")).toBe("green");
    expect(signalColor(released.shown.phase, released.shown.active, "west")).toBe("red");
  });

  it("holds a controller yellow long enough to see", () => {
    const started = stepLamps(
      play({ phase: "WEST_GREEN", active: "west" }),
      { phase: "YELLOW", active: "west" },
      0,
    );
    expect(started.shown).toEqual({ phase: "YELLOW", active: "west" });
    const still = stepLamps(started, { phase: "ALL_RED", active: "west" }, 400);
    expect(still.shown.phase).toBe("YELLOW");
    const after = stepLamps(still, { phase: "ALL_RED", active: "west" }, 1000);
    expect(after.shown.phase).toBe("ALL_RED");
  });
});
