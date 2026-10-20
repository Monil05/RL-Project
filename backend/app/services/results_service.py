"""Read-only access to the existing experiment CSV files."""

from __future__ import annotations

import csv
from pathlib import Path

from backend.app.services.errors import ApiError

SUMMARY_METRICS = (
    "average_waiting_time",
    "maximum_waiting_time",
    "average_queue_length",
    "maximum_queue_length",
    "throughput",
    "number_of_switches",
    "safety_violations",
    "cumulative_reward",
)


class ResultsService:
    def __init__(self, results_dir: Path) -> None:
        self._results_dir = results_dir

    def experiments(self) -> dict:
        rows = self._read("experiment_results.csv")
        names = []
        for row in rows:
            name = row.get("experiment") or ""
            if name and name not in names:
                names.append(name)
        return {
            "source": "results/experiment_results.csv",
            "timestamps_available": False,
            "experiments": [
                {
                    "id": name,
                    "name": name,
                    "records": sum(1 for row in rows if row.get("experiment") == name),
                }
                for name in names
            ],
        }

    def experiment(self, experiment_id: str) -> dict:
        rows = [row for row in self._read("experiment_results.csv") if row.get("experiment") == experiment_id]
        if not rows:
            raise ApiError(404, "Experiment not found in the existing results file.")
        return {
            "id": experiment_id,
            "source": "results/experiment_results.csv",
            "timestamps_available": False,
            "records": rows,
        }

    def results(self, **filters) -> dict:
        rows = self._filter(self._read("experiment_results.csv"), filters)
        return {
            "source": "results/experiment_results.csv",
            "timestamps_available": False,
            "count": len(rows),
            "records": rows,
        }

    def summary(self, **filters) -> dict:
        rows = self._filter(self._read("experiment_summary.csv"), filters)
        return {
            "source": "results/experiment_summary.csv",
            "timestamps_available": False,
            "count": len(rows),
            "records": [_with_differences(row, rows) for row in rows],
            "note": "Percentage columns compare a controller with Fixed Time in the same experiment and scenario. They are omitted when the Fixed Time value is zero or missing.",
        }

    def export_csv(self, **filters) -> str:
        rows = self._filter(self._read("experiment_results.csv"), filters)
        if not rows:
            return "experiment,scenario,controller\n"
        fieldnames = list(rows[0].keys())
        for row in rows[1:]:
            for key in row:
                if key not in fieldnames:
                    fieldnames.append(key)
        lines = [",".join(fieldnames)]
        for row in rows:
            lines.append(",".join(_csv_cell(row.get(name, "")) for name in fieldnames))
        return "\n".join(lines) + "\n"

    def _filter(self, rows: list[dict], filters: dict) -> list[dict]:
        filtered = rows
        for key in ("experiment", "scenario", "controller", "seed"):
            value = filters.get(key)
            if value is None or value == "":
                continue
            filtered = [row for row in filtered if str(row.get(key, "")) == str(value)]
        return filtered

    def _read(self, name: str) -> list[dict]:
        path = self._results_dir / name
        if not path.exists():
            return []
        with path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            rows = []
            for index, row in enumerate(reader):
                item = {"id": f"{name}:{index}"}
                item.update({key: _coerce(value) for key, value in row.items() if key is not None})
                rows.append(item)
            return rows


def _coerce(value: str):
    if value is None or value == "":
        return None
    try:
        if any(token in value for token in (".", "e", "E")):
            return float(value)
        return int(value)
    except ValueError:
        return value


def _csv_cell(value) -> str:
    text = "" if value is None else str(value)
    if any(character in text for character in (",", '"', "\n")):
        return '"' + text.replace('"', '""') + '"'
    return text


def _with_differences(row: dict, rows: list[dict]) -> dict:
    enriched = dict(row)
    baseline = next(
        (
            candidate
            for candidate in rows
            if candidate.get("experiment") == row.get("experiment")
            and candidate.get("scenario") == row.get("scenario")
            and candidate.get("controller") == "Fixed Time"
        ),
        None,
    )
    differences = {}
    for metric in SUMMARY_METRICS:
        differences[metric] = _percent(row.get(metric), None if baseline is None else baseline.get(metric))
    enriched["percent_difference_vs_fixed_time"] = differences
    return enriched


def _percent(value, baseline):
    if not isinstance(value, (int, float)) or not isinstance(baseline, (int, float)):
        return None
    if baseline == 0:
        return None
    return (float(value) - float(baseline)) / abs(float(baseline)) * 100.0
