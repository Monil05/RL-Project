import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { SimulationState } from "../types";

interface SimulationContextValue {
  state: SimulationState | null;
  connection: "unknown" | "online" | "offline";
  error: string | null;
  refresh: () => Promise<void>;
  send: (path: string, body?: unknown) => Promise<SimulationState | null>;
}

const SimulationContext = createContext<SimulationContextValue | null>(null);

export function SimulationProvider({ children }: { children: ReactNode }) {
  const [state, setState] = useState<SimulationState | null>(null);
  const [connection, setConnection] = useState<"unknown" | "online" | "offline">("unknown");
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const next = await api<SimulationState>("/api/simulation/state");
      setState(next);
      setConnection("online");
      setError(null);
    } catch (caught) {
      setConnection("offline");
      setError(caught instanceof Error ? caught.message : "The API is unreachable.");
    }
  }, []);

  const send = useCallback(async (path: string, body?: unknown) => {
    try {
      const next = await api<SimulationState>(path, {
        method: "POST",
        body: body === undefined ? JSON.stringify({}) : JSON.stringify(body),
      });
      setState(next);
      setConnection("online");
      setError(null);
      return next;
    } catch (caught) {
      const message = caught instanceof Error ? caught.message : "Request failed";
      setError(message);
      if (caught instanceof Error && "status" in caught && (caught as { status: number }).status === 0) {
        setConnection("offline");
      }
      return null;
    }
  }, []);

  useEffect(() => {
    void refresh();
    const timer = window.setInterval(() => void refresh(), 400);
    return () => window.clearInterval(timer);
  }, [refresh]);

  const value = useMemo(() => ({ state, connection, error, refresh, send }), [state, connection, error, refresh, send]);
  return <SimulationContext.Provider value={value}>{children}</SimulationContext.Provider>;
}

export function useSimulation() {
  const value = useContext(SimulationContext);
  if (!value) throw new Error("useSimulation must be used inside SimulationProvider");
  return value;
}
