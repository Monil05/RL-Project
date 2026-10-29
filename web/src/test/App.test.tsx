import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { Route, Routes } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { Layout } from "../components/Layout";
import { SimulationProvider } from "../context/SimulationContext";
import { ComparisonPage } from "../pages/ComparisonPage";
import { OverviewPage } from "../pages/OverviewPage";
import { ResultsPage } from "../pages/ResultsPage";
import { SimulationPage } from "../pages/SimulationPage";
import { TrainingPage } from "../pages/TrainingPage";
import type { SimulationState } from "../types";

const idleState: SimulationState = {
  ready: false,
  status: "idle",
  algorithm: "Fixed Time",
  scenario: "medium",
  lane_count: 2,
  free_left_turn: true,
  duration_seconds: 300,
  seed: 42,
  speed: 1,
  arrival_scale: 1,
  step_index: 0,
  vehicles_in_network: null,
  signal: null,
  queues: { north: [], south: [], east: [], west: [] },
  queue_lengths: { north: 0, south: 0, east: 0, west: 0 },
  departed: [],
  departure_log: [],
  phase_log: [],
  metrics: null,
  series: [],
  agent: null,
  error: null,
  message: "No simulation is loaded.",
};

function json(body: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));
}

function renderAt(path: string) {
  return render(
    <SimulationProvider>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route element={<Layout />}>
            <Route index element={<OverviewPage />} />
            <Route path="simulation" element={<SimulationPage />} />
            <Route path="training" element={<TrainingPage />} />
            <Route path="comparison" element={<ComparisonPage />} />
            <Route path="results" element={<ResultsPage />} />
          </Route>
        </Routes>
      </MemoryRouter>
    </SimulationProvider>,
  );
}

beforeEach(() => {
  vi.stubGlobal("fetch", vi.fn(async (input: RequestInfo) => {
    const url = String(input);
    if (url.includes("/api/simulation/state")) return json(idleState);
    if (url.includes("/api/results/summary")) {
      return json({
        records: [
          { id: "1", controller: "Fixed Time", average_waiting_time: 1.04, average_queue_length: 0.79, throughput: 226, number_of_switches: 0, cumulative_reward: 192.6, percent_difference_vs_fixed_time: { average_waiting_time: 0 } },
          { id: "2", controller: "Q-Learning", average_waiting_time: 1.05, average_queue_length: 0.8, throughput: 226, number_of_switches: 0.5, cumulative_reward: 191.3, percent_difference_vs_fixed_time: { average_waiting_time: 0.4 } },
        ],
      });
    }
    if (url.includes("/api/results")) {
      return json({ records: [{ id: "r1", experiment: "traffic_scenario", scenario: "high", controller: "SARSA", seed: 10, average_waiting_time: 1, average_queue_length: 1, throughput: 10, number_of_switches: 0, cumulative_reward: 1 }] });
    }
    if (url.includes("/api/project")) {
      return json({
        version: "1.0.0",
        algorithms: ["Fixed Time", "Q-Learning", "SARSA"],
        training_algorithms: ["Q-Learning", "SARSA"],
        scenarios: { medium: { north: 0.1 } },
        actions: ["KEEP", "SWITCH"],
        config: { signal: {}, reward: {}, learning: { episodes: 120, learning_rate: 0.1, discount_factor: 0.95, epsilon: 1, epsilon_decay: 0.995, minimum_epsilon: 0.05 }, simulation: {} },
        notes: [],
        streamlit_frontend: "streamlit run frontend/app.py",
      });
    }
    if (url.includes("/api/simulation/start")) return json({ ...idleState, status: "running", ready: true });
    if (url.includes("/api/training/start")) {
      return json({ id: "job1", status: "running", algorithm: "Q-Learning", scenario: "medium", seed: 42, config: {}, history: null, summary: null, error: null, current_episode: null, progress_available: false });
    }
    return json({ detail: "missing" }, 404);
  }));
});

describe("application shell", () => {
  it("shows the overview and an unavailable simulation", async () => {
    renderAt("/");
    expect(await screen.findByRole("heading", { name: "Overview" })).toBeInTheDocument();
    expect(await screen.findAllByText("Unavailable")).not.toHaveLength(0);
  });

  it("navigates to the simulation controls", async () => {
    renderAt("/");
    await userEvent.click(await screen.findByRole("link", { name: "Simulation" }));
    expect(await screen.findByRole("heading", { name: "Simulation" })).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Start" }));
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("/api/simulation/configure"), expect.anything());
  });

  it("shows a disconnected state when the API cannot be reached", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => Promise.reject(new Error("offline"))));
    renderAt("/");
    expect((await screen.findAllByRole("alert")).some((element) => element.textContent?.includes("unreachable"))).toBe(true);
    expect(screen.getByRole("button", { name: "Retry connection" })).toBeInTheDocument();
  });

  it("renders comparison bars from API rows", async () => {
    renderAt("/comparison");
    expect(await screen.findByText("Q-Learning")).toBeInTheDocument();
    expect(screen.getByText("+0.4%")).toBeInTheDocument();
  });

  it("filters results from the API response", async () => {
    renderAt("/results");
    expect(await screen.findByText("SARSA")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Controller"), "SARSA");
    expect(fetch).toHaveBeenCalledWith(expect.stringContaining("controller=SARSA"), expect.anything());
  });

  it("shows training in progress without a fake episode count", async () => {
    renderAt("/training");
    await userEvent.click(await screen.findByRole("button", { name: "Start training" }));
    expect(await screen.findByText(/Q-Learning is running/)).toBeInTheDocument();
    expect(screen.getByText(/does not report the current episode/)).toBeInTheDocument();
  });

  it("uses a collapsible sidebar on small screens", () => {
    renderAt("/");
    expect(document.querySelector("aside")?.className).toContain("md:translate-x-0");
  });
});
