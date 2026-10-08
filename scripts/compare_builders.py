"""Reproduce builder/client observations against a local Grafana checkout.

Run scripts/dev.py build first and set CARGO_TARGET_DIR or METRICRAFT_NATIVE_LIB.
This script performs no network requests. Results are observations, not a
language-conformance suite or a performance benchmark.
"""
import argparse
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grafana-checkout", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    sys.path[:0] = [str(ROOT / "python/metricraft/src"),
                   str(args.grafana_checkout.resolve() / "python")]
    from promql_builder.builders import promql as g
    from metricraft import QueryBuilder as n
    from metricraft._legacy.builder import MetricsBuilder as p
    from metricraft import DatabaseClient, VMSingleConfig
    from metricraft.config.http_options import HttpClientOptions

    def revision(path):
        return subprocess.check_output(["git", "-C", str(path), "rev-parse", "HEAD"], text=True).strip()

    result = {"grafana_revision": revision(args.grafana_checkout),
              "metricraft_base_revision": revision(ROOT),
              "note": "Public immutable Rust builder compared with Grafana and the historical Python fixture.",
              "cases": {}}
    cases = {
        "rate_sum": [lambda: g.sum(g.rate(g.vector("requests_total").range("5m"))).by(["job"]),
                     lambda: p.from_metric("requests_total").rate("5m").sum().by("job"),
                     lambda: n.from_metric("requests_total").rate("5m").sum().by("job")],
        "scalar": [lambda: g.n(42), lambda: p.from_scalar(42), lambda: n.from_scalar(42)],
        "filter": [lambda: g.vector("up").label("job", "api"),
                   lambda: p.from_metric("up").where_eq("job", "api"),
                   lambda: n.from_metric("up").where_eq("job", "api")],
        "topk": [lambda: g.topk(5, g.vector("up")), lambda: p.from_metric("up").topk(5),
                 lambda: n.from_metric("up").topk(5)],
        "label_replace": [lambda: g.label_replace(g.vector("up"), "dst", "$1", "src", "(.*)"),
                          lambda: p.from_metric("up").label_replace("dst", "$1", "src", "(.*)"),
                          lambda: n.from_metric("up").label_replace("dst", "$1", "src", "(.*)")],
        "vector_matching": [lambda: g.div(g.vector("a"), g.vector("b")).on(["job"]),
                            lambda: p.from_metric("a").div(p.from_metric("b")).on("job"),
                            lambda: n.from_metric("a").div(n.from_metric("b")).on("job")],
    }
    for case, makers in cases.items():
        result["cases"][case] = {}
        for index, (name, make) in enumerate(zip(("grafana", "python_legacy", "rust_native"), makers)):
            try:
                query = make()
                built = query.build()
                result["cases"][case][name] = {"build_type": type(built).__name__,
                                               "text": str(query) if index == 0 else built}
            except Exception as exc:
                result["cases"][case][name] = {"error": type(exc).__name__ + ": " + str(exc)}

    base = g.vector("up")
    derived = g.sum(base)
    base.label("env", "prod")
    result["shared_base"] = {"grafana": str(derived)}
    for name, factory in (("python_legacy", p), ("rust_native", n)):
        base = factory.from_metric("up")
        derived = base.sum()
        base.where_eq("env", "prod")
        result["shared_base"][name] = derived.build()

    class RecordingTransport:
        def __init__(self):
            self.calls = []

        def get(self, url, params=None):
            self.calls.append({"url": url, "params": params})
            return {"status": "success", "data": {"resultType": "matrix", "result": []}}

        def close(self):
            pass

    transport = RecordingTransport()
    config = VMSingleConfig("http://example.invalid", http_options=HttpClientOptions(client=transport))
    with DatabaseClient(config) as client:
        for query in (str(cases["rate_sum"][0]()), cases["rate_sum"][1](), cases["rate_sum"][2]()):
            response = client.query_range(query, start=0, end=300, step="30s")
            assert response.is_success
    assert len(transport.calls) == 3
    assert all(isinstance(call["params"]["query"], str) for call in transport.calls)
    result["client_requests"] = transport.calls
    content = json.dumps(result, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(content + "\n", encoding="utf-8")
    print(content)


if __name__ == "__main__":
    main()
