import { useEffect, useMemo, useState } from "react";
import { api, exportUrl } from "../api/client";
import { Button, Card, Empty, ErrorText, Field, fieldClass } from "../components/ui";
import type { ResultRecord } from "../types";

const COLUMNS = ["experiment", "scenario", "controller", "seed", "average_waiting_time", "average_queue_length", "throughput", "number_of_switches", "cumulative_reward"];

export function ResultsPage() {
  const [experiment, setExperiment] = useState("");
  const [scenario, setScenario] = useState("");
  const [controller, setController] = useState("");
  const [seed, setSeed] = useState("");
  const [sortKey, setSortKey] = useState("experiment");
  const [ascending, setAscending] = useState(true);
  const [rows, setRows] = useState<ResultRecord[]>([]);
  const [selected, setSelected] = useState<ResultRecord | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const params = new URLSearchParams();
    if (experiment) params.set("experiment", experiment);
    if (scenario) params.set("scenario", scenario);
    if (controller) params.set("controller", controller);
    if (seed) params.set("seed", seed);
    api<{ records: ResultRecord[] }>(`/api/results?${params}`)
      .then((payload) => {
        setRows(payload.records);
        setError(null);
      })
      .catch((caught: Error) => setError(caught.message));
  }, [experiment, scenario, controller, seed]);

  const sorted = useMemo(() => {
    return [...rows].sort((left, right) => {
      const a = left[sortKey];
      const b = right[sortKey];
      const result = String(a ?? "").localeCompare(String(b ?? ""), undefined, { numeric: true });
      return ascending ? result : -result;
    });
  }, [rows, sortKey, ascending]);

  function sortBy(key: string) {
    if (sortKey === key) setAscending(!ascending);
    else {
      setSortKey(key);
      setAscending(true);
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold">Experiment results</h1>
          <p className="mt-1 text-sm text-slate-600">Read-only view of the existing CSV files. Timestamps were not recorded.</p>
        </div>
        <a href={exportUrl({ experiment, scenario, controller, seed })}>
          <Button type="button">Export CSV</Button>
        </a>
      </div>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <Card>
        <div className="grid gap-3 md:grid-cols-4">
          <Field label="Experiment"><input className={fieldClass} value={experiment} onChange={(event) => setExperiment(event.target.value)} /></Field>
          <Field label="Scenario"><input className={fieldClass} value={scenario} onChange={(event) => setScenario(event.target.value)} /></Field>
          <Field label="Controller"><input className={fieldClass} value={controller} onChange={(event) => setController(event.target.value)} /></Field>
          <Field label="Seed"><input className={fieldClass} value={seed} onChange={(event) => setSeed(event.target.value)} /></Field>
        </div>
      </Card>
      {sorted.length === 0 ? <Empty title="No results" body="Nothing in the results file matches these filters." /> : (
        <Card>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead>
                <tr>
                  {COLUMNS.map((column) => (
                    <th key={column} className="py-2 pr-3">
                      <button className="text-xs font-semibold uppercase text-slate-500" onClick={() => sortBy(column)}>{column.replaceAll("_", " ")}</button>
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {sorted.map((row) => (
                  <tr key={String(row.id)} className="cursor-pointer border-t border-slate-100 hover:bg-slate-50" onClick={() => setSelected(row)}>
                    {COLUMNS.map((column) => <td key={column} className="py-2 pr-3">{String(row[column] ?? "")}</td>)}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      )}
      {selected ? (
        <Card title="Record detail" action={<Button tone="ghost" onClick={() => setSelected(null)}>Close</Button>}>
          <p className="mb-3 text-sm text-slate-500">Recorded at: not present in the existing results file.</p>
          <dl className="grid gap-2 sm:grid-cols-2">
            {Object.entries(selected).map(([key, value]) => (
              <div key={key} className="rounded-lg bg-slate-50 px-3 py-2">
                <dt className="text-xs uppercase text-slate-500">{key}</dt>
                <dd className="text-sm text-slate-800">{String(value)}</dd>
              </div>
            ))}
          </dl>
        </Card>
      ) : null}
    </div>
  );
}
