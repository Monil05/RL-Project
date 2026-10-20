import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Card, Empty, ErrorText, Stat, formatNumber } from "../components/ui";
import { useSimulation } from "../context/SimulationContext";
import { IntersectionCanvas } from "../simulation/IntersectionCanvas";
import type { ResultRecord } from "../types";

export function OverviewPage() {
  const { state, connection, error } = useSimulation();
  const [summary, setSummary] = useState<ResultRecord[] | null>(null);
  const [summaryError, setSummaryError] = useState<string | null>(null);
  const metrics = state?.metrics;

  useEffect(() => {
    api<{ records: ResultRecord[] }>("/api/results/summary?experiment=traffic_scenario&scenario=medium")
      .then((payload) => setSummary(payload.records))
      .catch((caught: Error) => setSummaryError(caught.message));
  }, []);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Overview</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Adaptive traffic signal control for one four-way intersection. Fixed Time, Q-Learning, and SARSA are compared using the existing simulator.
        </p>
      </div>
      {connection === "offline" ? <ErrorText>{error ?? "The API is unreachable."}</ErrorText> : null}
      <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
        <Stat label="Status" value={state?.status ?? "Unavailable"} hint={state?.ready ? state.algorithm : "No simulation loaded"} />
        <Stat label="Vehicles in network" value={metrics ? String(state?.vehicles_in_network ?? 0) : "Unavailable"} />
        <Stat label="Average wait" value={formatNumber(metrics?.average_waiting_time)} hint="seconds" />
        <Stat label="Average queue" value={formatNumber(metrics?.average_queue_length)} hint="vehicles" />
        <Stat label="Throughput" value={metrics ? String(metrics.throughput) : "Unavailable"} hint="departed vehicles" />
        <Stat label="Signal switches" value={metrics ? String(metrics.number_of_switches) : "Unavailable"} />
        <Stat label="Simulation time" value={metrics ? `${metrics.time}s` : "Unavailable"} hint={state ? `of ${state.duration_seconds}s` : undefined} />
        <Stat label="Controller" value={state?.algorithm ?? "Unavailable"} hint={state?.scenario ? `${state.scenario} demand` : undefined} />
      </div>
      <div className="grid gap-4 lg:grid-cols-5">
        <Card title="Intersection" className="lg:col-span-3">
          <IntersectionCanvas state={state} />
          <div className="mt-3 flex flex-wrap gap-3 text-xs text-slate-500">
            <Legend color="#dc2626" label="Straight" />
            <Legend color="#2563eb" label="Left" />
            <Legend color="#16a34a" label="Right" />
          </div>
        </Card>
        <Card title="Current run" className="lg:col-span-2">
          {state?.series?.length ? (
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={state.series}>
                  <CartesianGrid stroke="#e2e8f0" />
                  <XAxis dataKey="time" tick={{ fontSize: 12 }} />
                  <YAxis tick={{ fontSize: 12 }} />
                  <Tooltip />
                  <Line type="monotone" dataKey="average_waiting_time" name="Avg wait (s)" stroke="#4f46e5" dot={false} />
                  <Line type="monotone" dataKey="average_queue_length" name="Avg queue" stroke="#0f766e" dot={false} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            <Empty title="No series yet" body="Start a simulation to plot waiting time and queue length from the Python environment." />
          )}
          <div className="mt-4 flex gap-3 text-sm">
            <Link className="font-semibold text-accent" to="/simulation">Open simulation</Link>
            <Link className="font-semibold text-accent" to="/comparison">Open comparison</Link>
          </div>
        </Card>
      </div>
      <Card title="Historical comparison, medium scenario">
        <p className="mb-3 text-sm text-slate-500">Stored experiment summary. This is not the live simulation.</p>
        {summaryError ? <ErrorText>{summaryError}</ErrorText> : null}
        {summary && summary.length === 0 ? <Empty title="No stored rows" body="results/experiment_summary.csv has no medium traffic_scenario rows." /> : null}
        {summary && summary.length > 0 ? (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="text-xs uppercase text-slate-500">
                <tr>
                  <th className="py-2">Controller</th>
                  <th>Avg wait (s)</th>
                  <th>Avg queue</th>
                  <th>Throughput</th>
                  <th>Switches</th>
                  <th>vs Fixed Time wait</th>
                </tr>
              </thead>
              <tbody>
                {summary.map((row) => (
                  <tr key={String(row.id)} className="border-t border-slate-100">
                    <td className="py-2 font-medium">{String(row.controller)}</td>
                    <td>{formatNumber(row.average_waiting_time as number)}</td>
                    <td>{formatNumber(row.average_queue_length as number)}</td>
                    <td>{String(row.throughput)}</td>
                    <td>{String(row.number_of_switches)}</td>
                    <td>{formatPercentSafe(row)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : null}
      </Card>
    </div>
  );
}

function Legend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-2">
      <span className="h-2.5 w-2.5 rounded-sm" style={{ background: color }} />
      {label}
    </span>
  );
}

function formatPercentSafe(row: ResultRecord): string {
  const value = row.percent_difference_vs_fixed_time?.average_waiting_time;
  if (value === null || value === undefined) return "—";
  return `${value > 0 ? "+" : ""}${value.toFixed(1)}%`;
}
