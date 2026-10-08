"""Synthetic configurable-monitoring workloads, not a production trace replay."""
import argparse
import gc
import json
from pathlib import Path
import statistics
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "python/metricraft/src"))
from metricraft import QueryBuilder
from metricraft._legacy.builder import MetricsBuilder


def selector(builder, metric):
    query = builder.from_metric(metric)
    for index in range(8):
        query = query.where_eq("filter_" + str(index), "value_" + str(index))
    return query


def workload(builder, name):
    if name == "error_ratio":
        base = selector(builder, "http_requests_total")
        total = base.rate("5m").sum().by("job")
        errors = base.where_regex("status", "5..").rate("5m").sum().by("job")
        return [100 * errors / total]
    if name == "latency_quantile":
        base = selector(builder, "http_request_duration_seconds_bucket")
        return [base.rate("5m").sum().by("job", "le").histogram_quantile(0.95)]
    if name == "dashboard_fanout":
        base = selector(builder, "http_requests_total")
        return [base.where_eq("instance", str(i)).rate("5m").sum().by("job") for i in range(16)]
    raise ValueError("unknown workload: " + name)


def measure(builder, name, iterations, rounds):
    for _ in range(10):
        [query.build() for query in workload(builder, name)]
    samples = {name: [] for name in ("construct", "render", "release", "total")}
    example = [query.build() for query in workload(builder, name)]
    for _ in range(rounds):
        gc.collect()
        totals = dict.fromkeys(samples, 0)
        for _ in range(iterations):
            t0 = time.perf_counter_ns()
            queries = workload(builder, name)
            t1 = time.perf_counter_ns()
            texts = [query.build() for query in queries]
            t2 = time.perf_counter_ns()
            del queries, texts
            t3 = time.perf_counter_ns()
            for phase, elapsed in (("construct", t1-t0), ("render", t2-t1),
                                   ("release", t3-t2), ("total", t3-t0)):
                totals[phase] += elapsed
        for phase in samples:
            samples[phase].append(totals[phase] / iterations / 1000)
    return {"queries_per_iteration": len(example), "example": example,
            "phases": {phase: {"median_us": statistics.median(values), "rounds_us": values}
                       for phase, values in samples.items()}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=200)
    parser.add_argument("--rounds", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if min(args.iterations, args.rounds) < 1:
        parser.error("iterations and rounds must be positive")
    report = {"note": "Synthetic workloads; GC and validation enabled. Times are per workload, not per query. No HTTP.",
              "iterations": args.iterations, "rounds": args.rounds, "workloads": {}}
    for name in ("error_ratio", "latency_quantile", "dashboard_fanout"):
        report["workloads"][name] = {
            label: measure(builder, name, args.iterations, args.rounds)
            for label, builder in (("legacy_python", MetricsBuilder), ("rust_via_ctypes", QueryBuilder))
        }
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Completed synthetic workload comparison:", args.output)


if __name__ == "__main__":
    main()
