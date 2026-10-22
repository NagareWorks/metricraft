"""Build the browser demo from the same Rust core as the Python SDK."""
import os
from pathlib import Path
import subprocess

ROOT = Path(__file__).resolve().parents[1]
manifest = ROOT / "wasm/Cargo.toml"
target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "wasm/target")).resolve()
output = ROOT / "public/playground-wasm"
output.mkdir(parents=True, exist_ok=True)


def run(*args):
    subprocess.run(args, cwd=ROOT, check=True)


version = subprocess.check_output(["wasm-bindgen", "--version"], text=True).strip()
if version != "wasm-bindgen 0.2.122":
    raise SystemExit("Install the pinned CLI: cargo install wasm-bindgen-cli --version 0.2.122 --locked")
run("cargo", "build", "--manifest-path", str(manifest), "--locked", "--release",
    "--target", "wasm32-unknown-unknown", "--target-dir", str(target))
run("wasm-bindgen", str(target / "wasm32-unknown-unknown/release/metricraft_playground.wasm"),
    "--target", "web", "--out-dir", str(output), "--out-name", "builder")
