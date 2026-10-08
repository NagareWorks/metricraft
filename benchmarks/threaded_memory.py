"""Bounded concurrent ctypes stress with persistent workers and shared roots."""
import argparse
from concurrent.futures import ThreadPoolExecutor
import gc
import json
import math
from pathlib import Path
import sys
import time
import tracemalloc
import weakref

from python_memory import process_memory, snapshot
from metricraft import QueryBuilder as Q


def churn(base, batch_size):
    roots = []
    failures = 0
    for index in range(batch_size):
        selected = base.where_eq("instance", str(index))
        rate = selected.rate("5m").sum().by("job")
        roots.append(rate / (rate + 1))
        if index % 8 == 0:
            try:
                selected.where_eq("bad\nlabel", "value")
            except ValueError:
                failures += 1
            else:
                raise AssertionError("invalid labels accepted")
        if index % 16 == 0:
            rate.to_debug_json(max_items=1000)
    del selected, rate
    refs = [weakref.ref(query) for query in roots]
    for query in roots:
        query.build("promql")
        try:
            query.build("promql", max_output_bytes=1)
        except ValueError:
            failures += 1
        else:
            raise AssertionError("output limit ignored")
    del query, roots
    if any(ref() is not None for ref in refs):
        raise AssertionError("a worker retained a Python query owner")
    return batch_size, failures


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seconds", type=float, default=60)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--batch-size", type=int, default=128)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if not math.isfinite(args.seconds) or args.seconds <= 0 or min(args.workers, args.batch_size) < 1:
        parser.error("duration, workers and batch size must be positive and finite")
    base = Q.from_metric("http_requests_total")
    for index in range(32):
        base = base.where_eq("filter_" + str(index), "x" * 64)
    original = base.build("promql")
    process_memory()
    total = failures = batches = 0
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        # Force all workers to initialize before memory tracing and measurement.
        from threading import Barrier
        barrier = Barrier(args.workers)
        def warmup():
            barrier.wait(timeout=30)
            churn(base, args.batch_size)
        futures = [pool.submit(warmup) for _ in range(args.workers)]
        for future in futures:
            future.result()
        del future, futures
        gc.collect()
        tracemalloc.start()
        samples = [snapshot("warmed_workers")]
        started = time.monotonic()
        next_sample = started + 5
        while time.monotonic() - started < args.seconds:
            futures = [pool.submit(churn, base, args.batch_size) for _ in range(args.workers)]
            for future in futures:
                queries, errors = future.result()
                total += queries
                failures += errors
            del future, futures
            batches += 1
            assert base.build("promql") == original
            if time.monotonic() >= next_sample:
                samples.append(snapshot("released_batch_" + str(batches)))
                next_sample = time.monotonic() + 5
        samples.append(snapshot("released_final_batch"))
    elapsed = time.monotonic() - started
    del base
    samples.append(snapshot("workers_and_base_released"))
    tracemalloc.stop()
    report = vars(args).copy()
    report.pop("output")
    report.update(elapsed_seconds=elapsed, queries=total, expected_errors=failures,
                  batches=batches, samples=samples,
                  note="Synthetic concurrent create/build/error/drop workload. Weakrefs verify owner release; RSS/private bytes include caches and are not a native leak counter. Tracing is enabled, so throughput is not a timing benchmark.")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(f"Released {total} query owners across {args.workers} workers; handled {failures} expected errors in {elapsed:.2f}s")


if __name__ == "__main__":
    main()
