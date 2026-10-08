"""Evaluate SDK-generated and persisted query text on isolated, pinned backends."""
import argparse
import asyncio
from contextlib import contextmanager
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python/metricraft/src"), str(ROOT / "tests/conformance")]
from evaluation import cases, series
from metricraft import DatabaseClient, PrometheusConfig, VMSingleConfig


def request(url, data=None):
    with urlopen(Request(url, data=data), timeout=5) as response:
        return response.read()


def port():
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        return listener.getsockname()[1]


@contextmanager
def backend(command, health, log_path):
    with log_path.open("wb") as log:
        process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT,
                                   creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        try:
            deadline = time.monotonic() + 30
            while True:
                if process.poll() is not None:
                    raise RuntimeError("backend exited; see " + str(log_path))
                try:
                    request(health)
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise TimeoutError("backend did not become ready; see " + str(log_path))
                    time.sleep(0.1)
            yield
        finally:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=15)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=10)


def labels_text(labels):
    metric = labels["__name__"]
    fields = [key + "=" + json.dumps(value, ensure_ascii=False)
              for key, value in sorted(labels.items()) if key != "__name__"]
    return metric + "{" + ",".join(fields) + "}"


def compare(result, expected, timestamp):
    if not result.is_success or result.result_type != "vector" or result.is_partial:
        raise AssertionError("expected complete vector: " + repr(result))
    actual = {}
    for item in result.result:
        key = tuple(sorted(item["metric"].items()))
        if key in actual:
            raise AssertionError("duplicate result label set")
        when, value = item["value"]
        if float(when) != timestamp:
            raise AssertionError("unexpected sample timestamp: " + repr(when))
        actual[key] = float(value)
    wanted = {tuple(sorted(labels.items())): value for labels, value in expected}
    if actual.keys() != wanted.keys():
        raise AssertionError("label sets differ: actual=" + repr(actual) + " expected=" + repr(wanted))
    for key, value in wanted.items():
        if not math.isclose(actual[key], value, rel_tol=1e-7, abs_tol=1e-9):
            raise AssertionError("value differs: actual=" + repr(actual) + " expected=" + repr(wanted))


def evaluate(config, mode, start, output, report, matrix=None):
    generated = [case for case in cases(start) if mode in case.modes]
    saved = output / (mode + "-queries.json")
    saved.write_text(json.dumps({case.name: case.query.build(mode, experimental_functions=case.experimental_functions,
                                                          features=case.features) for case in generated}, indent=2), encoding="utf-8")
    texts = json.loads(saved.read_text(encoding="utf-8"))
    with DatabaseClient(config) as client:
        from catalog import evaluate as evaluate_catalog
        evaluate_catalog(client, mode, start, matrix, report)
        for case in generated:
            row = {"mode": mode, "name": case.name, "query": texts[case.name],
                   "expected": case.expected, "status": "failed"}
            report["cases"].append(row)
            result = client.query(texts[case.name], time=start + 600)
            row["actual"] = result.data
            compare(result, case.expected, start + 600)
            if case.range_check:
                result = client.query_range(texts[case.name], start=start + 480, end=start + 600, step="60s")
                if not result.is_success or result.result_type != "matrix" or result.is_partial:
                    raise AssertionError("expected complete matrix")
                # Check every grid point and reject missing, extra or reordered timestamps.
                expected_times = [start + index * 60 for index in (8, 9, 10)]
                for item in result.result:
                    if [float(pair[0]) for pair in item["values"]] != expected_times:
                        raise AssertionError("unexpected range timestamps")
                from metricraft import MetricsQueryResult
                for position, index in enumerate((8, 9, 10)):
                    samples = [{"metric": item["metric"], "value": item["values"][position]} for item in result.result]
                    expected = next(c.expected for c in cases(start, index) if c.name == case.name)
                    compare(MetricsQueryResult("success", {"resultType": "vector", "result": samples}), expected, start + index * 60)
                row["range_actual"] = result.data
            row["status"] = "passed"
        # Direct builder arguments select the backend too; persisted strings use
        # the already chosen build mode recorded above.
        compare(client.query(generated[0].query, time=start + 600), generated[0].expected, start + 600)
        if mode == "promql":
            from metricraft import QueryBuilder as Q
            try:
                client.query(Q.from_metric("mc_missing").default(0), time=start + 600)
            except ValueError:
                pass
            else:
                raise AssertionError("Prometheus client accepted a MetricsQL-only builder")

    async def async_check():
        case = generated[0]
        async with DatabaseClient(config) as client:
            result = await client.query_async(texts[case.name], time=start + 600)
            compare(result, case.expected, start + 600)
            compare(await client.query_async(case.query, time=start + 600), case.expected, start + 600)
    asyncio.run(async_check())
    report["async_clients"].append(mode)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--prometheus", default="prometheus")
    parser.add_argument("--promtool", default="promtool")
    parser.add_argument("--victoria-metrics", default="victoria-metrics-prod")
    parser.add_argument("--matrix", type=Path, help="generated compatibility matrix for full catalog acceptance")
    args = parser.parse_args()
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents or output.exists():
        parser.error("output must be a new directory outside the checkout")
    paths = {}
    for key in ("prometheus", "promtool", "victoria_metrics"):
        resolved = shutil.which(getattr(args, key))
        if not resolved:
            parser.error(key + " executable is required")
        paths[key] = str(Path(resolved).resolve())
    output.mkdir(parents=True)
    report = {"status": "failed", "cases": [], "async_clients": [], "versions": {}}
    try:
        for key, executable in paths.items():
            version = subprocess.check_output([executable, "--version" if key != "victoria_metrics" else "-version"], stderr=subprocess.STDOUT, text=True, timeout=30)
            pinned = "v1.153.0" if key == "victoria_metrics" else "version 3.15.0"
            if not re.search(re.escape(pinned) + r"(?:[-\s,(]|$)", version):
                raise RuntimeError(key + " must match pinned " + pinned)
            report["versions"][key] = version.strip()
        report["binary_sha256"] = {name: hashlib.sha256(Path(path).read_bytes()).hexdigest() for name, path in paths.items()}
        native = os.environ.get("METRICRAFT_NATIVE_LIB")
        if not native:
            raise RuntimeError("set METRICRAFT_NATIVE_LIB to the library under test")
        report["native_sha256"] = hashlib.sha256(Path(native).read_bytes()).hexdigest()
        report["revision"] = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
        report["dirty"] = bool(subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT))
        report["source_sha256"] = {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                   for base, pattern in ((ROOT / "crates", "*.rs"), (ROOT / "python/metricraft/src", "*.py"), (ROOT / "tests/conformance", "*.py"), (ROOT / "scripts", "check_backend_results.py"))
                                   for p in base.rglob(pattern)}
        start = int(time.time() // 60) * 60 - 1200
        report["fixture_start"] = start
        fixture = series() + [
            {"metric": {"__name__": name, "job": "api", "instance": "one", "le": "1"},
             "values": list(range(11))}
            for name in ("metricraft_a", "a", "b")
        ]
        fixture.append({"metric": {"__name__": "metricraft_b", "job": "worker", "instance": "two"},
                        "values": list(range(11))})
        (output / "fixture.json").write_text(json.dumps(fixture, ensure_ascii=False), encoding="utf-8")
        text = "\n".join(labels_text(row["metric"]) + " " + str(value) + " " + str(start + index * 60)
                         for row in fixture for index, value in enumerate(row["values"])) + "\n# EOF\n"
        (output / "fixture.om").write_bytes(text.encode("utf-8"))
        storage = output / "prometheus-data"
        with (output / "import.log").open("w") as log:
            subprocess.run([paths["promtool"], "tsdb", "create-blocks-from", "openmetrics", str(output / "fixture.om"), str(storage)], stdout=log, stderr=subprocess.STDOUT, check=True, timeout=120)
        (output / "prometheus.json").write_text(json.dumps({"global": {"scrape_interval": "1m"}, "scrape_configs": []}), encoding="utf-8")
        url = "http://127.0.0.1:" + str(port())
        from extensions import FEATURES
        with backend([paths["prometheus"], "--enable-feature=promql-experimental-functions," + ",".join(FEATURES), "--config.file=" + str(output / "prometheus.json"), "--storage.tsdb.path=" + str(storage), "--web.listen-address=" + url[len("http://"):]], url + "/-/ready", output / "prometheus.log"):
            evaluate(PrometheusConfig(url), "promql", start, output, report, args.matrix)
        url = "http://127.0.0.1:" + str(port())
        with backend([paths["victoria_metrics"], "-storageDataPath=" + str(output / "victoria-metrics-data"), "-httpListenAddr=" + url[len("http://"):], "-memory.allowedBytes=128MiB", "-search.disableCache"], url + "/health", output / "victoria-metrics.log"):
            payload = "\n".join(json.dumps(dict(row, timestamps=[(start + i * 60) * 1000 for i in range(11)])) for row in fixture).encode()
            request(url + "/api/v1/import", payload)
            request(url + "/internal/force_flush")
            evaluate(VMSingleConfig(url), "metricsql", start, output, report, args.matrix)
        if report.get("catalog_failures"):
            raise AssertionError("catalog acceptance failed:\n" + "\n".join(report["catalog_failures"]))
        report["status"] = "passed"
    except Exception as exc:
        report["error"] = str(exc)
        raise
    finally:
        (output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        lines = ["# Backend result conformance", "", "Status: " + report["status"], "",
                 "Pinned Prometheus 3.15.0 / VictoriaMetrics 1.153.0; synthetic fixtures and independent expected values.", "",
                 "| Mode | Case | Status |", "| --- | --- | --- |"]
        lines += [f"| {row['mode']} | {row['name']} | {row['status']} |" for row in report["cases"]]
        if "catalog" in report:
            from collections import Counter
            counts = Counter((row["mode"], row["status"]) for row in report["catalog"])
            lines += ["", "## Official catalog acceptance", "",
                      "Instant and range requests from the generated compatibility matrix. Accepted signatures do not imply numerical equivalence.", "",
                      "| Mode | Status | Probes |", "| --- | --- | ---: |"]
            lines += [f"| {mode} | {status} | {count} |" for (mode, status), count in sorted(counts.items())]
        if "error" in report:
            lines += ["", "Failure: " + report["error"]]
        lines += ["", "Async client checks: " + ", ".join(report["async_clients"]), "",
                  "Witness coverage only, not full language equivalence. All backend processes are scoped to this run."]
        (output / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        print("Backend result reports:", output)


if __name__ == "__main__":
    main()
