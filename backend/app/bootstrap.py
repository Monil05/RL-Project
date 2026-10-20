"""Put the existing project root on sys.path without moving any core modules."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

GENERATED_DIR = ROOT / "generated" / "videos"
RESULTS_DIR = ROOT / "results"
APP_VERSION = "1.0.0"
