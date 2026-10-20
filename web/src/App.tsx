import { BrowserRouter, Route, Routes } from "react-router-dom";
import { ErrorBoundary } from "./components/ErrorBoundary";
import { Layout } from "./components/Layout";
import { SimulationProvider } from "./context/SimulationContext";
import { ComparisonPage } from "./pages/ComparisonPage";
import { OverviewPage } from "./pages/OverviewPage";
import { ResultsPage } from "./pages/ResultsPage";
import { SettingsPage } from "./pages/SettingsPage";
import { SimulationPage } from "./pages/SimulationPage";
import { TrainingPage } from "./pages/TrainingPage";
import { VideoPage } from "./pages/VideoPage";

export function App() {
  return (
    <ErrorBoundary>
      <SimulationProvider>
        <BrowserRouter>
          <Routes>
            <Route element={<Layout />}>
              <Route index element={<OverviewPage />} />
              <Route path="simulation" element={<SimulationPage />} />
              <Route path="training" element={<TrainingPage />} />
              <Route path="comparison" element={<ComparisonPage />} />
              <Route path="results" element={<ResultsPage />} />
              <Route path="video" element={<VideoPage />} />
              <Route path="settings" element={<SettingsPage />} />
            </Route>
          </Routes>
        </BrowserRouter>
      </SimulationProvider>
    </ErrorBoundary>
  );
}
