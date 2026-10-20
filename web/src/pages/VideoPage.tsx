import { useEffect, useState } from "react";
import { api } from "../api/client";
import { Button, Card, Empty, ErrorText, Field, Loading, Notice, fieldClass } from "../components/ui";
import type { VideoJob } from "../types";

export function VideoPage() {
  const [algorithm, setAlgorithm] = useState("Fixed Time");
  const [scenario, setScenario] = useState("low");
  const [duration, setDuration] = useState(8);
  const [fps, setFps] = useState(8);
  const [frames, setFrames] = useState(1);
  const [laneCount, setLaneCount] = useState(2);
  const [job, setJob] = useState<VideoJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running")) return;
    const timer = window.setInterval(() => {
      api<VideoJob>(`/api/video/status/${job.id}`).then(setJob).catch((caught: Error) => setError(caught.message));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  async function generate() {
    setPending(true);
    setError(null);
    try {
      const created = await api<VideoJob>("/api/video/generate", {
        method: "POST",
        body: JSON.stringify({
          algorithm,
          scenario,
          duration_seconds: duration,
          fps,
          frames_per_step: frames,
          lane_count: laneCount,
        }),
      });
      setJob(created);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Video request failed");
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Video and export</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Rendering uses the existing imageio exporter. It does not report partial progress. The form starts from a short clip because the exporter keeps every frame in memory. The API rejects more than 400 frames.
        </p>
      </div>
      <Notice>Q-Learning and SARSA clips need a completed agent for the same scenario. A failed render stays failed. It is not shown as a video.</Notice>
      {error ? <ErrorText>{error}</ErrorText> : null}
      <div className="grid gap-4 lg:grid-cols-[320px_minmax(0,1fr)]">
        <Card title="Render settings">
          <div className="space-y-3">
            <Field label="Controller">
              <select className={fieldClass} value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}>
                <option>Fixed Time</option>
                <option>Q-Learning</option>
                <option>SARSA</option>
              </select>
            </Field>
            <Field label="Scenario">
              <select className={fieldClass} value={scenario} onChange={(event) => setScenario(event.target.value)}>
                {["low", "medium", "high", "balanced", "asymmetric", "unseen"].map((name) => <option key={name}>{name}</option>)}
              </select>
            </Field>
            <Field label="Lanes">
              <select className={fieldClass} value={laneCount} onChange={(event) => setLaneCount(Number(event.target.value))}>
                <option value={2}>2</option>
                <option value={4}>4</option>
              </select>
            </Field>
            <Field label="Duration (seconds)">
              <input className={fieldClass} type="number" min={1} value={duration} onChange={(event) => setDuration(Number(event.target.value))} />
            </Field>
            <Field label="Frames per step">
              <input className={fieldClass} type="number" min={1} value={frames} onChange={(event) => setFrames(Number(event.target.value))} />
            </Field>
            <Field label="Frames per second">
              <input className={fieldClass} type="number" min={1} value={fps} onChange={(event) => setFps(Number(event.target.value))} />
            </Field>
            <Button disabled={pending || job?.status === "running" || job?.status === "queued"} onClick={() => void generate()}>Generate video</Button>
          </div>
        </Card>
        <Card title="Output">
          {!job ? <Empty title="No render yet" body="Generate a clip to call the existing video pipeline." /> : null}
          {job && (job.status === "queued" || job.status === "running") ? <Loading label={`Render is ${job.status}. Progress is not available from the exporter.`} /> : null}
          {job?.status === "failed" ? <ErrorText>{job.error ?? "Rendering failed."}</ErrorText> : null}
          {job?.status === "completed" && job.download_url ? (
            <div className="space-y-3">
              <video className="w-full rounded-lg bg-slate-900" controls src={job.download_url}>
                <track kind="captions" />
              </video>
              <a className="text-sm font-semibold text-accent" href={job.download_url}>Download MP4</a>
            </div>
          ) : null}
        </Card>
      </div>
    </div>
  );
}
