export interface LampPhase {
  phase: string;
  active: string | null;
}

export interface LampPlayback {
  shown: LampPhase;
  holdDirection: string | null;
  holdUntil: number;
  pending: LampPhase | null;
}

export const YELLOW_HOLD_MS = 1000;

const GREEN_PHASES: Record<string, string> = {
  NORTH_GREEN: "north",
  SOUTH_GREEN: "south",
  EAST_GREEN: "east",
  WEST_GREEN: "west",
};

export function greenDirection(lamp: LampPhase): string | null {
  return GREEN_PHASES[lamp.phase] ?? null;
}

function samePhase(left: LampPhase, right: LampPhase): boolean {
  return left.phase === right.phase && left.active === right.active;
}

export function stepLamps(state: LampPlayback, server: LampPhase, now: number, holdMs = YELLOW_HOLD_MS): LampPlayback {
  if (state.holdDirection && now < state.holdUntil) {
    return { ...state, pending: server };
  }

  const released: LampPlayback = state.holdDirection
    ? { shown: state.pending ?? state.shown, holdDirection: null, holdUntil: 0, pending: null }
    : state;

  if (samePhase(released.shown, server)) {
    return { shown: server, holdDirection: null, holdUntil: 0, pending: null };
  }

  if (server.phase === "YELLOW" && server.active) {
    return {
      shown: { phase: "YELLOW", active: server.active },
      holdDirection: server.active,
      holdUntil: now + holdMs,
      pending: server,
    };
  }

  const leaving = greenDirection(released.shown);
  const arriving = greenDirection(server);
  if (leaving && leaving !== arriving) {
    return {
      shown: { phase: "YELLOW", active: leaving },
      holdDirection: leaving,
      holdUntil: now + holdMs,
      pending: server,
    };
  }

  return { shown: server, holdDirection: null, holdUntil: 0, pending: null };
}
