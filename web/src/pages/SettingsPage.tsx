import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Card, ErrorText, Loading } from "../components/ui";
import { useSimulation } from "../context/SimulationContext";
import type { ProjectInfo } from "../types";

export function SettingsPage() {
  const { connection, refresh } = useSimulation();
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [health, setHealth] = useState<string>("unknown");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([api<ProjectInfo>("/api/project"), api<{ status: string; version: string }>("/api/health")])
      .then(([info, status]) => {
        setProject(info);
        setHealth(`${status.status} · ${status.version}`);
        setError(null);
      })
      .catch((caught: Error) => setError(caught.message));
  }, [connection]);

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Settings and project</h1>
        <p className="mt-1 text-sm text-slate-600">These values are the existing simulator defaults. This page does not rewrite them.</p>
      </div>
      {error ? <ErrorText>{error} <button className="ml-2 underline" onClick={() => void refresh()}>Retry</button></ErrorText> : null}
      {!project && !error ? <Loading label="Loading project information" /> : null}
      {project ? (
        <div className="grid gap-4 lg:grid-cols-2">
          <Card title="Connection">
            <dl className="space-y-2 text-sm">
              <Row label="Backend" value={connection} />
              <Row label="Health" value={health} />
              <Row label="Application version" value={project.version} />
              <Row label="Streamlit frontend" value={project.streamlit_frontend} />
            </dl>
          </Card>
          <Card title="Algorithms and actions">
            <p className="text-sm text-slate-700">Controllers: {project.algorithms.join(", ")}</p>
            <p className="mt-2 text-sm text-slate-700">Actions: {project.actions.join(", ")}</p>
            <p className="mt-2 text-sm text-slate-700">Scenarios: {Object.keys(project.scenarios).join(", ")}</p>
          </Card>
          <Card title="Signal defaults">
            <DefinitionList data={project.config.signal} />
          </Card>
          <Card title="Reward defaults">
            <DefinitionList data={project.config.reward} />
          </Card>
          <Card title="Learning defaults">
            <DefinitionList data={project.config.learning} />
          </Card>
          <Card title="Notes">
            <ul className="list-disc space-y-2 pl-5 text-sm text-slate-700">
              {project.notes.map((note) => <li key={note}>{note}</li>)}
            </ul>
          </Card>
        </div>
      ) : null}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-slate-100 py-2">
      <dt className="text-slate-500">{label}</dt>
      <dd className="font-medium text-slate-800">{value}</dd>
    </div>
  );
}

function DefinitionList({ data }: { data: Record<string, number> }) {
  return (
    <dl className="space-y-1 text-sm">
      {Object.entries(data).map(([key, value]) => (
        <div key={key} className="flex justify-between gap-4">
          <dt className="text-slate-500">{key.replaceAll("_", " ")}</dt>
          <dd className="font-medium">{value}</dd>
        </div>
      ))}
    </dl>
  );
}
