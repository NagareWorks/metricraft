"""Run browser-binding, copied-snippet and backend differential checks portably."""
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
SITE = ROOT / "website"
target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target")).resolve()
env = dict(os.environ, PYTHONUTF8="1", PYTHONPATH=str(ROOT / "python/metricraft/src"))


def run(*args, cwd=ROOT):
    subprocess.run(args, cwd=cwd, env=env, check=True)


run("cargo", "fmt", "--manifest-path", "website/wasm/Cargo.toml", "--", "--check")
run("cargo", "test", "--manifest-path", "website/wasm/Cargo.toml", "--locked")
run("cargo", "clippy", "--manifest-path", "website/wasm/Cargo.toml", "--all-targets", "--locked", "--", "-D", "warnings")
run("cargo", "build", "-p", "metricraft-ffi", "--locked", "--target-dir", str(target))
name = "metricraft_ffi.dll" if sys.platform == "win32" else "libmetricraft_ffi.dylib" if sys.platform == "darwin" else "libmetricraft_ffi.so"
env["METRICRAFT_NATIVE_LIB"] = str(target / "debug" / name)
run(sys.executable, "scripts/check-examples.py", cwd=SITE)
run("node", "scripts/check-playground.mjs", cwd=SITE)
