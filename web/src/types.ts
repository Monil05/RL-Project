export type JobStatus = "queued" | "running" | "completed" | "failed" | "cancelled";

export interface Vehicle {
  id: number;
  direction: string;
  movement: string;
  lane_index: number;
  arrival_time: number | null;
}

export interface Metrics {
  time: number;
  phase: string;
  average_waiting_time: number;
  maximum_waiting_time: number;
  average_queue_length: number;
  maximum_queue_length: number;
  throughput: number;
  average_travel_time: number;
  number_of_stops: number;
  number_of_switches: number;
  safety_violations: number;
  illegal_switch_attempts: number;
  vehicles_exceeding_max_wait: number;
  cumulative_reward: number;
  last_reward: number | null;
}

export interface SeriesPoint {
  time: number;
  average_waiting_time: number;
  average_queue_length: number;
  throughput: number;
  cumulative_reward: number;
  number_of_switches: number;
}

export interface SimulationState {
  ready: boolean;
  status: "idle" | "running" | "paused" | "completed";
  algorithm: string;
  scenario: string;
  lane_count: number;
  free_left_turn: boolean;
  duration_seconds: number;
  seed: number;
  speed: number;
  arrival_scale: number;
  step_index: number;
  vehicles_in_network: number | null;
  signal: {
    phase: string;
    active_direction: string | null;
    elapsed_green_time: number;
    green_directions: string[];
    switches: number;
    illegal_switch_attempts: number;
    safety_violations: number;
  } | null;
  queues: Record<string, Vehicle[]>;
  queue_lengths: Record<string, number>;
  departed: Vehicle[];
  departure_log: { step_index: number; departed: Vehicle[] }[];
  phase_log: { step_index: number; phase: string; active_direction: string | null }[];
  metrics: Metrics | null;
  series: SeriesPoint[];
  agent: {
    job_id: string;
    algorithm: string;
    scenario: string;
    seed: number;
    episodes: number;
    duration_seconds: number;
  } | null;
  error: string | null;
  message: string | null;
}

export interface ProjectInfo {
  version: string;
  algorithms: string[];
  training_algorithms: string[];
  scenarios: Record<string, Record<string, number>>;
  actions: string[];
  config: {
    signal: Record<string, number>;
    reward: Record<string, number>;
    learning: Record<string, number>;
    simulation: Record<string, unknown>;
  };
  notes: string[];
  streamlit_frontend: string;
}

export interface TrainingJob {
  id: string;
  status: JobStatus;
  algorithm: string;
  scenario: string;
  seed: number;
  config: ProjectInfo["config"];
  history: {
    episode: number;
    reward: number;
    average_waiting_time: number;
    average_queue_length: number;
    throughput: number;
    epsilon: number;
    training_time_seconds?: number;
  }[] | null;
  summary: {
    episodes: number;
    last_episode_reward: number | null;
    sum_of_episode_rewards: number | null;
    last_average_waiting_time: number | null;
    last_throughput: number | null;
    last_epsilon: number | null;
    training_time_seconds: number | null;
  } | null;
  error: string | null;
  current_episode: number | null;
  progress_available: boolean;
}

export interface ResultRecord {
  id: string;
  experiment?: string;
  scenario?: string | number;
  controller?: string;
  seed?: number | null;
  average_waiting_time?: number | null;
  average_queue_length?: number | null;
  throughput?: number | null;
  cumulative_reward?: number | null;
  number_of_switches?: number | null;
  percent_difference_vs_fixed_time?: Record<string, number | null>;
  [key: string]: unknown;
}

export interface VideoJob {
  id: string;
  status: JobStatus;
  algorithm: string;
  scenario: string;
  error: string | null;
  download_url: string | null;
  progress_available: boolean;
}

export class ApiRequestError extends Error {
  status: number;

  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
