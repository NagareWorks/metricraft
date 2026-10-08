#!/usr/bin/env python3
"""
Quick timing for the Python API backed by the Rust query engine.
Measures construction and rendering without network calls.

Usage:
  python benchmarks/python_baseline_timings.py \
      --iterations 500 \
      --output baseline_timings.json
"""

from __future__ import annotations

import argparse
import json
import statistics
import time
from dataclasses import dataclass, asdict
from typing import Callable, Dict, List

from metricraft import QueryBuilder


def _make_simple():
    return QueryBuilder.from_metric("cpu_usage")


def _make_medium():
    return (
        QueryBuilder.from_metric("cpu_usage")
        .sum().by("instance")
    )


def _make_complex():
    return (
        QueryBuilder.from_metric("cpu_usage")
        .sum().by("instance")
        .avg().by("service")
    )


def _p95(values: List[float]) -> float:
    if not values:
        return 0.0
    if len(values) < 20:
        return max(values)
    return statistics.quantiles(values, n=20)[18]


@dataclass
class TimingStats:
    count: int
    mean_ms: float
    median_ms: float
    p95_ms: float


def _measure(name: str, maker: Callable[[], object], iterations: int) -> Dict[str, TimingStats]:
    build_times: List[float] = []
    build_times_str: List[float] = []

    # warmup
    for _ in range(min(20, iterations)):
        q = maker()
        _ = q.build()

    for _ in range(iterations):
        t0 = time.perf_counter()
        q = maker()
        t1 = time.perf_counter()
        _ = q.build()
        t2 = time.perf_counter()
        build_times.append((t1 - t0) * 1000.0)
        build_times_str.append((t2 - t1) * 1000.0)

    def stats(samples: List[float]) -> TimingStats:
        return TimingStats(
            count=len(samples),
            mean_ms=statistics.mean(samples) if samples else 0.0,
            median_ms=statistics.median(samples) if samples else 0.0,
            p95_ms=_p95(samples),
        )

    return {
        f"{name}_build": stats(build_times),
        f"{name}_stringify": stats(build_times_str),
    }


def main():
    parser = argparse.ArgumentParser(description="Baseline timings for Python query building")
    parser.add_argument("--iterations", type=int, default=200, help="iterations per case")
    parser.add_argument("--output", type=str, default="baseline_timings.json", help="output JSON path")
    args = parser.parse_args()

    results: Dict[str, TimingStats] = {}
    for label, fn in [
        ("simple", _make_simple),
        ("medium", _make_medium),
        ("complex", _make_complex),
    ]:
        results.update(_measure(label, fn, args.iterations))

    serializable = {k: asdict(v) for k, v in results.items()}
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(serializable, f, indent=2)
    print(json.dumps(serializable, indent=2))


if __name__ == "__main__":
    main()
