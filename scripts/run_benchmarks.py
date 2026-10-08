"""Build and run the unified benchmark suite; keep generated reports outside Git."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import platform
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]


def provenance():
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"], cwd=ROOT
    ).decode().split("\0")
    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(),
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip(),
        "dirty": bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT)),
        "platform": platform.platform(), "machine": platform.machine(),
        "python": sys.version, "cpu_count": os.cpu_count(),
        "rustc": subprocess.check_output(["rustc", "--version"], text=True).strip(),
        "source_sha256": {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                          for name in sorted(set(paths)) if name and (ROOT / name).is_file()
                          and (Path(name).suffix in (".py", ".rs", ".toml", ".yml") or name.endswith("Cargo.lock"))},
    }


def summary(report, output):
    lines = ["# MetriCraft benchmarks", "", "Synthetic workloads; release build, validation and GC enabled. No production latency claim.",
             "Shared-runner timings are observational; failures in lifetime/limit checks still fail the run.", "",
             f"Revision: `{report.get('revision', 'unavailable')}`", "",
             f"Working tree modified: {report.get('dirty', 'unavailable')}. Status: {report['status']}.", "",
             "| Check | Status | Seconds |", "| --- | --- | ---: |"]
    lines += [f"| {step['name']} | {step['status']} | {step['seconds']:.2f} |" for step in report["steps"]]
    if "error" in report:
        lines += ["", "Failure: " + report["error"], ""]
    timings = output / "workloads.json"
    passed = {step["name"] for step in report["steps"] if step["status"] == "passed"}
    if "workloads" in passed:
        data = json.loads(timings.read_text(encoding="utf-8"))
        lines += ["", "## Synthetic application workloads", "",
                  "Times include construction, rendering and release, per workload iteration.", "",
                  "| Workload | Queries | Python µs | Rust via ctypes µs | Ratio |",
                  "| --- | ---: | ---: | ---: | ---: |"]
        for name, result in data["workloads"].items():
            old = result["legacy_python"]["phases"]["total"]["median_us"]
            new = result["rust_via_ctypes"]["phases"]["total"]["median_us"]
            count = result["rust_via_ctypes"]["queries_per_iteration"]
            lines.append(f"| {name} | {count} | {old:.2f} | {new:.2f} | {old / new:.2f}x |")
    if {"microbenchmarks", "rust-timings"} <= passed:
        native = json.loads((output / "rust-timings.json").read_text(encoding="utf-8"))
        binding = json.loads((output / "microbenchmarks.json").read_text(encoding="utf-8"))
        lines += ["", "## Matching selector/rate/aggregation shapes", "",
                  "Construction, rendering and release, µs per query. The ctypes column includes the Python facade and ownership costs.", "",
                  "| Shape | Pure Rust µs | Rust via ctypes µs | Historical Python µs |",
                  "| --- | ---: | ---: | ---: |"]
        for name, timing in native.items():
            row = binding["workloads"][name]
            ffi = row["rust_via_ctypes"]["construct_render_release"]["median_us"]
            old = row["legacy_python"]["construct_render_release"]["median_us"]
            lines.append(f"| {name} | {timing['construct_render_release_us']:.2f} | {ffi:.2f} | {old:.2f} |")
    memory = output / "threaded-memory.json"
    if "threaded-memory" in passed:
        data = json.loads(memory.read_text(encoding="utf-8"))
        lines += ["", "## Concurrent memory workload", "",
                  f"{data['workers']} workers released {data['queries']} query owners and handled "
                  f"{data['expected_errors']} expected validation/limit failures in {data['elapsed_seconds']:.1f}s.", "",
                  "| Sample | Python live bytes | Process private bytes / RSS |",
                  "| --- | ---: | ---: |"]
        for sample in data["samples"]:
            lines.append(f"| {sample['phase']} | {sample['python_live_bytes']} | "
                         f"{sample.get('private_bytes', sample.get('resident_bytes', 'unavailable'))} |")
        lines += ["", "Process memory includes allocator caches and measurement records; it is not a leak counter."]
    lines += ["", "The artifact includes phase timings, pure Rust timings, native allocation accounting, "
              "single-thread and concurrent memory samples, logs and source/binary hashes."]
    return "\n".join(lines) + "\n"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--memory-seconds", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args(argv)
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("output must be outside the checkout")
    if min(args.iterations, args.rounds, args.workers) < 1 or not math.isfinite(args.memory_seconds) or args.memory_seconds <= 0:
        parser.error("iterations, rounds, workers and memory-seconds must be positive and finite")
    if output.exists() and (not output.is_dir() or any(output.iterdir())):
        parser.error("output must be a new or empty directory to avoid mixing runs")
    output.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env.update(PYTHONDONTWRITEBYTECODE="1", PYTHONUTF8="1", PYTHONIOENCODING="utf-8")
    env["PYTHONPATH"] = str(ROOT / "python/metricraft/src")
    target = Path(env.get("CARGO_TARGET_DIR", output.parent / "benchmark-target")).resolve()
    env["CARGO_TARGET_DIR"] = str(target)
    native = "metricraft_ffi.dll" if sys.platform == "win32" else "libmetricraft_ffi.dylib" if sys.platform == "darwin" else "libmetricraft_ffi.so"
    library = target / "release" / native
    env["METRICRAFT_NATIVE_LIB"] = str(library)
    report = {"status": "failed", "steps": [], "settings": {key: value for key, value in vars(args).items() if key != "output"}}

    def run(name, command, data_file=None):
        print("Running " + name, flush=True)
        started = time.monotonic()
        step = {"name": name, "command": command, "status": "failed", "seconds": 0}
        report["steps"].append(step)
        try:
            with (output / (name + ".log")).open("w", encoding="utf-8") as log:
                if data_file:
                    with (output / data_file).open("w", encoding="utf-8") as data:
                        subprocess.run(command, cwd=ROOT, env=env, stdout=data, stderr=log, check=True)
                else:
                    subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
            step["status"] = "passed"
        finally:
            step["seconds"] = time.monotonic() - started

    try:
        report.update(provenance())
        run("release-build", ["cargo", "build", "--workspace", "--release", "--locked"])
        report["native_sha256"] = hashlib.sha256(library.read_bytes()).hexdigest()
        run("native-allocation", ["cargo", "run", "--release", "--locked", "-p", "metricraft-core", "--example", "memory_profile"])
        run("rust-timings", ["cargo", "run", "--quiet", "--release", "--locked", "-p", "metricraft-core", "--example", "benchmark_shapes", "--", str(args.iterations), str(args.rounds)], "rust-timings.json")
        for name, script in (("microbenchmarks", "compare_immutable.py"), ("workloads", "workloads.py")):
            run(name, [sys.executable, "benchmarks/" + script, "--iterations", str(args.iterations), "--rounds", str(args.rounds), "--output", str(output / (name + ".json"))])
        run("python-memory", [sys.executable, "benchmarks/python_memory.py", "--output", str(output / "python-memory.json")])
        run("threaded-memory", [sys.executable, "benchmarks/threaded_memory.py", "--seconds", str(args.memory_seconds), "--workers", str(args.workers), "--output", str(output / "threaded-memory.json")])
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (output / "summary.md").write_text(summary(report, output), encoding="utf-8")
        print("Benchmark reports: " + str(output), flush=True)


if __name__ == "__main__":
    main()
