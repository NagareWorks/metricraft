"""Run the complete unified Python test suite without generating coverage files."""
from pathlib import Path
import subprocess
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    raise SystemExit(subprocess.call([sys.executable, str(root / "scripts/dev.py"), "tests"]))
