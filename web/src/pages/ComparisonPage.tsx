import { useEffect, useState } from "react";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { Card, Empty, ErrorText, Field, Notice, fieldClass, formatNumber, formatPercent } from "../components/ui";
import type { ResultRecord } from "../types";

export function ComparisonPage() {
  const [experiment, setExperiment] = useState("traffic_scenario");
  const [scenario, setScenario] = useState("high");
  const [seed, setSeed] = useState("");
  const [rows, setRows] = useState<ResultRecord[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams({ experiment, scenario });
    if (seed) params.set("seed", seed);
    const path = seed ? `/api/results?${params}` : `/api/results/summary?${params}`;
    api<{ records: ResultRecord[] }>(path)
      .then((payload) => {
        setRows(payload.records);
        setError(null);
      })
      .catch((caught: Error) => setError(caught.message));
  }, [experiment, scenario, seed]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Algorithm comparison</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          These figures come from the stored experiment files. A negative waiting-time difference means a lower wait than Fixed Time. It is not a claim that one controller is generally better.
        </p>
      </div>
      <Notice>The high-demand summary is the saved case where the controllers are not identical. Medium demand in the same file is effectively tied.</Notice>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Card>
        <div className="grid gap-3 md:grid-cols-3">
          <Field label="Experiment">
            <select className={fieldClass} value={experiment} onChange={(event) => setExperiment(event.target.value)}>
              <option value="traffic_scenario">traffic_scenario</option>
              <option value="maximum_green">maximum_green</option>
              <option value="maximum_wait">maximum_wait</option>
            </select>
          </Field>
          <Field label="Scenario or sweep value">
            <input className={fieldClass} value={scenario} onChange={(event) => setScenario(event.target.value)} />
          </Field>
          <Field label="Seed (raw rows only)">
            <input className={fieldClass} value={seed} onChange={(event) => setSeed(event.target.value)} placeholder="Leave blank for the summary" />
          </Field>
        </div>
      </Card>
      {rows.length === 0 ? <Empty title="No rows" body="No stored records match this experiment and scenario." /> : null}
      {rows.length > 0 ? (
        <>
          <Card title="Average waiting time">
            <div className="h-72">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={rows.map((row) => ({ name: String(row.controller), wait: Number(row.average_waiting_time ?? 0) }))}>
                  <CartesianGrid stroke="#e2e8f0" />
                  <XAxis dataKey="name" />
                  <YAxis />
                  <Tooltip />
                  <Bar dataKey="wait" name="Avg wait (s)" fill="#4f46e5" radius={4} />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </Card>
          <Card title={seed ? "Raw evaluation rows" : "Summary rows"}>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-sm">
                <thead className="text-xs uppercase text-slate-500">
                  <tr>
                    <th className="py-2">Controller</th>
                    <th>Avg wait (s)</th>
                    <th>Avg queue</th>
                    <th>Throughput</th>
                    <th>Switches</th>
                    <th>Reward</th>
                    <th>Wait vs Fixed Time</th>
                  </tr>
                </thead>
                <tbody>
                  {rows.map((row) => (
                    <tr key={String(row.id)} className="border-t border-slate-100">
                      <td className="py-2 font-medium">{String(row.controller)}</td>
                      <td>{formatNumber(row.average_waiting_time as number)}</td>
                      <td>{formatNumber(row.average_queue_length as number)}</td>
                      <td>{String(row.throughput ?? "")}</td>
                      <td>{String(row.number_of_switches ?? "")}</td>
                      <td>{formatNumber(row.cumulative_reward as number)}</td>
                      <td>{formatPercent(row.percent_difference_vs_fixed_time?.average_waiting_time)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            {seed ? <p className="mt-3 text-xs text-slate-500">Seed filters read experiment_results.csv. Percentage differences are calculated on the summary endpoint, so this raw view leaves that column blank.</p> : null}
          </Card>
        </>
      ) : null}
    </div>
  );
}
