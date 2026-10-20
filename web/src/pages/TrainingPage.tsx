import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { Button, Card, Empty, ErrorText, Field, Loading, Notice, Stat, fieldClass, formatNumber } from "../components/ui";
import type { ProjectInfo, TrainingJob } from "../types";

export function TrainingPage() {
  const [project, setProject] = useState<ProjectInfo | null>(null);
  const [algorithm, setAlgorithm] = useState("Q-Learning");
  const [scenario, setScenario] = useState("medium");
  const [episodes, setEpisodes] = useState("");
  const [learningRate, setLearningRate] = useState("");
  const [discount, setDiscount] = useState("");
  const [epsilon, setEpsilon] = useState("");
  const [decay, setDecay] = useState("");
  const [minimumEpsilon, setMinimumEpsilon] = useState("");
  const [duration, setDuration] = useState("");
  const [seed, setSeed] = useState("42");
  const [job, setJob] = useState<TrainingJob | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    api<ProjectInfo>("/api/project").then(setProject).catch((caught: Error) => setError(caught.message));
  }, []);

  useEffect(() => {
    if (!job || (job.status !== "queued" && job.status !== "running")) return;
    const timer = window.setInterval(() => {
      api<TrainingJob>(`/api/training/status/${job.id}`)
        .then(setJob)
        .catch((caught: Error) => setError(caught.message));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [job?.id, job?.status]);

  async function start() {
    setPending(true);
    setError(null);
    const body: Record<string, unknown> = {
      algorithm,
      scenario,
      seed: Number(seed),
    };
    if (episodes) body.episodes = Number(episodes);
    if (learningRate) body.learning_rate = Number(learningRate);
    if (discount) body.discount_factor = Number(discount);
    if (epsilon) body.epsilon = Number(epsilon);
    if (decay) body.epsilon_decay = Number(decay);
    if (minimumEpsilon) body.minimum_epsilon = Number(minimumEpsilon);
    if (duration) body.duration_seconds = Number(duration);
    try {
      const created = await api<TrainingJob>("/api/training/start", { method: "POST", body: JSON.stringify(body) });
      setJob(created);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Training failed to start");
    } finally {
      setPending(false);
    }
  }

  async function cancel() {
    if (!job) return;
    try {
      const next = await api<TrainingJob>(`/api/training/cancel/${job.id}`, { method: "POST" });
      setJob(next);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Cancel failed");
    }
  }

  const learning = project?.config.learning;
  return (
    <div className="space-y-4">
      <div>
        <h1 className="text-2xl font-semibold">Training centre</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-600">
          Blank hyperparameter fields keep the existing defaults. Episode charts appear after the trainer returns. A running job cannot be interrupted.
        </p>
      </div>
      {error ? <ErrorText>{error}</ErrorText> : null}
      {!project && !error ? <Loading label="Loading defaults" /> : null}
      <div className="grid gap-4 lg:grid-cols-[340px_minmax(0,1fr)]">
        <Card title="Run">
          <div className="space-y-3">
            <Field label="Algorithm">
              <select className={fieldClass} value={algorithm} onChange={(event) => setAlgorithm(event.target.value)}>
                <option>Q-Learning</option>
                <option>SARSA</option>
              </select>
            </Field>
            <Field label="Scenario">
              <select className={fieldClass} value={scenario} onChange={(event) => setScenario(event.target.value)}>
                {Object.keys(project?.scenarios ?? { medium: {} }).map((name) => <option key={name}>{name}</option>)}
              </select>
            </Field>
            <Field label={`Episodes (default ${learning?.episodes ?? "…"})`}>
              <input className={fieldClass} value={episodes} onChange={(event) => setEpisodes(event.target.value)} inputMode="numeric" />
            </Field>
            <Field label={`Learning rate (default ${learning?.learning_rate ?? "…"})`}>
              <input className={fieldClass} value={learningRate} onChange={(event) => setLearningRate(event.target.value)} />
            </Field>
            <Field label={`Discount factor (default ${learning?.discount_factor ?? "…"})`}>
              <input className={fieldClass} value={discount} onChange={(event) => setDiscount(event.target.value)} />
            </Field>
            <Field label={`Epsilon (default ${learning?.epsilon ?? "…"})`}>
              <input className={fieldClass} value={epsilon} onChange={(event) => setEpsilon(event.target.value)} />
            </Field>
            <Field label={`Epsilon decay (default ${learning?.epsilon_decay ?? "…"})`}>
              <input className={fieldClass} value={decay} onChange={(event) => setDecay(event.target.value)} />
            </Field>
            <Field label={`Minimum epsilon (default ${learning?.minimum_epsilon ?? "…"})`}>
              <input className={fieldClass} value={minimumEpsilon} onChange={(event) => setMinimumEpsilon(event.target.value)} />
            </Field>
            <Field label="Episode length in seconds (default 300)">
              <input className={fieldClass} value={duration} onChange={(event) => setDuration(event.target.value)} />
            </Field>
            <Field label="Seed">
              <input className={fieldClass} value={seed} onChange={(event) => setSeed(event.target.value)} />
            </Field>
            <div className="flex gap-2">
              <Button disabled={pending || job?.status === "running" || job?.status === "queued"} onClick={() => void start()}>Start training</Button>
              <Button tone="secondary" disabled={!job || (job.status !== "queued" && job.status !== "running")} onClick={() => void cancel()}>Cancel</Button>
            </div>
          </div>
        </Card>
        <div className="space-y-4">
          <Card title="Job">
            {!job ? <Empty title="No job in this session" body="Start training to call the existing Q-Learning or SARSA function." /> : null}
            {job?.status === "queued" || job?.status === "running" ? (
              <div className="space-y-2">
                <Loading label={`${job.algorithm} is ${job.status}`} />
                <Notice>The existing training function does not report the current episode until it finishes.</Notice>
              </div>
            ) : null}
            {job?.status === "failed" ? <ErrorText>{job.error ?? "Training failed."}</ErrorText> : null}
            {job?.status === "cancelled" ? <Notice>The backend confirmed this job was cancelled before training started.</Notice> : null}
            {job?.summary ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <Stat label="Episodes" value={String(job.summary.episodes)} />
                <Stat label="Last episode reward" value={formatNumber(job.summary.last_episode_reward)} />
                <Stat label="Sum of episode rewards" value={formatNumber(job.summary.sum_of_episode_rewards)} hint="Sum of each episode's cumulative reward" />
                <Stat label="Last avg wait" value={formatNumber(job.summary.last_average_waiting_time)} />
              </div>
            ) : null}
          </Card>
          <Card title="Episode reward">
            {job?.history?.length ? (
              <div className="h-72">
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={job.history}>
                    <CartesianGrid stroke="#e2e8f0" />
                    <XAxis dataKey="episode" />
                    <YAxis />
                    <Tooltip />
                    <Line type="monotone" dataKey="reward" name="Episode reward" stroke="#4f46e5" dot={false} />
                    <Line type="monotone" dataKey="average_waiting_time" name="Avg wait (s)" stroke="#0f766e" dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <Empty title="No history yet" body="Reward by episode is available after training completes." />
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
