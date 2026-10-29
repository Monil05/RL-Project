import { useState } from "react";
import type { LampPhase } from "../simulation/signalPlayback";
import { Pause, Play, RotateCcw } from "lucide-react";
import { Button, Card, ErrorText, Field, Notice, Stat, fieldClass, formatNumber } from "../components/ui";
import { useSimulation } from "../context/SimulationContext";
import { IntersectionCanvas } from "../simulation/IntersectionCanvas";

const SCENARIOS = ["low", "medium", "high", "balanced", "asymmetric", "unseen"];

export function SimulationPage() {
  const { state, error, send } = useSimulation();
  const [algorithm, setAlgorithm] = useState("Fixed Time");
  const [scenario, setScenario] = useState("medium");
  const [laneCount, setLaneCount] = useState(2);
  const [freeLeft, setFreeLeft] = useState(true);
  const [duration, setDuration] = useState(120);
  const [seed, setSeed] = useState(42);
  const [speed, setSpeed] = useState(1);
  const [arrivalScale, setArrivalScale] = useState(4);
  const [pending, setPending] = useState(false);
  const [lamp, setLamp] = useState<LampPhase | null>(null);

  async function apply(startAfter: boolean) {
    setPending(true);
    const configured = await send("/api/simulation/configure", {
      algorithm,
      scenario,
      lane_count: laneCount,
      free_left_turn: freeLeft,
      duration_seconds: duration,
      seed,
      speed,
      arrival_scale: arrivalScale,
    });
    if (configured && startAfter) await send("/api/simulation/start");
    setPending(false);
  }

  const metrics = state?.metrics;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Simulation</h1>
        <p className="mt-1 text-sm text-slate-600">
          Playback steps the existing Python environment. Busy traffic adds more arrivals so queues form on red. Training still uses the original scenario rates.
        </p>
      </div>
      {error ? <ErrorText>{error}</ErrorText> : null}
      {algorithm !== "Fixed Time" ? (
        <Notice>Q-Learning and SARSA need a completed training job for the same scenario and lane layout. Use Original density to match that training traffic.</Notice>
      ) : null}
      <div className="grid gap-4 xl:grid-cols-[320px_minmax(0,1fr)]">
        <Card title="Controls">
          <div className="space-y-3">
            <Field label="Controller">
              <select className={fieldClass} value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}>
                <option>Fixed Time</option>
                <option>Q-Learning</option>
                <option>SARSA</option>
              </select>
            </Field>
            <Field label="Traffic scenario">
              <select className={fieldClass} value={scenario} onChange={(event) => setScenario(event.target.value)}>
                {SCENARIOS.map((name) => <option key={name}>{name}</option>)}
              </select>
            </Field>
            <Field label="Traffic density">
              <select className={fieldClass} value={arrivalScale} onChange={(event) => setArrivalScale(Number(event.target.value))}>
                <option value={1}>Original</option>
                <option value={2.5}>Steady</option>
                <option value={4}>Busy</option>
              </select>
            </Field>
            <Field label="Lanes">
              <select className={fieldClass} value={laneCount} onChange={(event) => setLaneCount(Number(event.target.value))}>
                <option value={2}>2 lanes</option>
                <option value={4}>4 lanes</option>
              </select>
            </Field>
            <Field label="Duration (seconds)">
              <input className={fieldClass} type="number" min={1} max={3600} value={duration} onChange={(event) => setDuration(Number(event.target.value))} />
            </Field>
            <Field label="Seed">
              <input className={fieldClass} type="number" min={0} value={seed} onChange={(event) => setSeed(Number(event.target.value))} />
            </Field>
            <Field label={`Speed ${speed.toFixed(2)}x`}>
              <input type="range" min={0.25} max={4} step={0.25} value={speed} onChange={(event) => {
                const next = Number(event.target.value);
                setSpeed(next);
                void send("/api/simulation/configure", {
                  algorithm: state?.algorithm ?? algorithm,
                  scenario: state?.scenario ?? scenario,
                  lane_count: state?.lane_count ?? laneCount,
                  free_left_turn: state?.free_left_turn ?? freeLeft,
                  duration_seconds: state?.duration_seconds ?? duration,
                  seed: state?.seed ?? seed,
                  speed: next,
                  arrival_scale: state?.arrival_scale ?? arrivalScale,
                });
              }} />
            </Field>
            <label className="flex items-center gap-2 text-sm text-slate-700">
              <input type="checkbox" checked={freeLeft} onChange={(event) => setFreeLeft(event.target.checked)} />
              Free left turn
            </label>
            <div className="flex flex-wrap gap-2">
              <Button disabled={pending || state?.status === "running"} onClick={() => void apply(true)}><Play className="h-4 w-4" /> Start</Button>
              <Button tone="secondary" disabled={pending || state?.status !== "running"} onClick={() => void send("/api/simulation/pause")}><Pause className="h-4 w-4" /> Pause</Button>
              <Button tone="secondary" disabled={pending || state?.status !== "paused"} onClick={() => void send("/api/simulation/start")}>Resume</Button>
              <Button tone="secondary" disabled={pending} onClick={() => void send("/api/simulation/reset")}><RotateCcw className="h-4 w-4" /> Reset</Button>
            </div>
          </div>
        </Card>
        <div className="space-y-4">
          <Card title={`${state?.algorithm ?? "Controller"} · ${state?.scenario ?? "scenario"}`}>
            <IntersectionCanvas state={state} onLamp={setLamp} />
            <div className="mt-3 grid gap-2 text-sm text-slate-600 sm:grid-cols-3">
              <div>Phase: {lamp?.phase ?? state?.signal?.phase ?? "Unavailable"}</div>
              <div>Active approach: {lamp?.active ?? state?.signal?.active_direction ?? "None"}</div>
              <div>Step {state?.step_index ?? 0}</div>
            </div>
          </Card>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-5">
            <Stat label="Time" value={metrics ? `${metrics.time}s` : "Unavailable"} />
            <Stat label="Avg wait" value={formatNumber(metrics?.average_waiting_time)} />
            <Stat label="Vehicles waiting" value={state?.vehicles_in_network != null ? String(state.vehicles_in_network) : "Unavailable"} />
            <Stat label="Throughput" value={metrics ? String(metrics.throughput) : "Unavailable"} />
            <Stat label="Switches" value={metrics ? String(metrics.number_of_switches) : "Unavailable"} />
          </div>
          {state?.agent ? (
            <Notice>Using {state.agent.algorithm} agent {state.agent.job_id.slice(0, 8)}, trained for {state.agent.episodes} episodes on {state.agent.scenario}.</Notice>
          ) : null}
        </div>
      </div>
    </div>
  );
}
