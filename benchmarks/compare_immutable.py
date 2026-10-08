"""Local construction/render/reuse timings; no HTTP or backend latency included."""

import argparse
import gc
import hashlib
import json
import os
from pathlib import Path
import platform
import statistics
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [
    str(ROOT / "python/metricraft/src"),
]
from metricraft import QueryBuilder as Native
from metricraft._legacy.builder import MetricsBuilder as Legacy


def construct(builder, size):
    query = builder.from_metric("http_requests_total")
    for i in range(size):
        query = query.where_eq("label_" + str(i), "value_" + str(i))
    return query.rate("5m").sum().by("job")


def measure(call, iterations, rounds):
    for _ in range(min(20, iterations)):
        call()
    times = []
    # Leave GC enabled: Python ownership/finalizer costs belong to the measurement.
    for _ in range(rounds):
        gc.collect()
        started = time.perf_counter_ns()
        for _ in range(iterations):
            call()
        times.append((time.perf_counter_ns() - started) / iterations / 1000)
    return {
        "median_us": statistics.median(times),
        "min_us": min(times),
        "max_us": max(times),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=300)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.iterations <= 0 or args.rounds <= 0:
        parser.error("iterations and rounds must be positive")
    library = os.environ.get("METRICRAFT_NATIVE_LIB")
    if not library:
        parser.error("set METRICRAFT_NATIVE_LIB explicitly to a release-mode library")
    diff = subprocess.check_output(["git", "diff", "HEAD", "--binary"], cwd=ROOT)
    paths = subprocess.check_output(
        ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        text=True,
    ).split("\0")
    sources = {}
    for name in sorted(set(paths)):
        path = ROOT / name
        if path.is_file() and (
            path.suffix in (".rs", ".py", ".toml") or path.name == "Cargo.lock"
        ):
            sources[name] = hashlib.sha256(path.read_bytes()).hexdigest()
    result = {
        "revision": subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
        ).strip(),
        "working_tree_patch_sha256": hashlib.sha256(diff).hexdigest(),
        "native_library_sha256": hashlib.sha256(Path(library).read_bytes()).hexdigest(),
        "native_profile_directory": Path(library).parent.name,
        "source_sha256": sources,
        "platform": platform.platform(),
        "python": sys.version,
        "iterations": args.iterations,
        "rounds": args.rounds,
        "note": "Microbenchmarks with GC enabled. Both render paths validate. No HTTP, memory profiling, or production speedup claim.",
        "workloads": {},
    }
    for size in (1, 8, 32):
        workloads = {}
        for name, builder in (("legacy_python", Legacy), ("rust_via_ctypes", Native)):
            built = construct(builder, size)
            base = builder.from_metric("http_requests_total")
            rendered = built.build()
            for i in range(size):
                assert 'label_{}="value_{}"'.format(i, i) in rendered
            assert "rate(" in rendered and "job" in rendered
            workloads[name] = {
                "construct_and_release": measure(
                    lambda: construct(builder, size), args.iterations, args.rounds
                ),
                "render_existing": measure(built.build, args.iterations, args.rounds),
                "construct_render_release": measure(
                    lambda: construct(builder, size).build(),
                    args.iterations,
                    args.rounds,
                ),
                "branch_from_shared_selector": measure(
                    lambda: base.where_eq("job", "api").rate("5m").build(),
                    args.iterations,
                    args.rounds,
                ),
                "rendered_example": rendered,
            }
            assert base.build() == "http_requests_total"
        result["workloads"][str(size) + "_labels"] = workloads
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")
    for size, workloads in result["workloads"].items():
        for phase in (
            "construct_and_release",
            "render_existing",
            "construct_render_release",
        ):
            old = workloads["legacy_python"][phase]["median_us"]
            new = workloads["rust_via_ctypes"][phase]["median_us"]
            print(
                f"{size:10} {phase:25} legacy={old:9.2f}us native={new:9.2f}us ratio={old/new:.2f}x"
            )


if __name__ == "__main__":
    main()
