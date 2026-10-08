"""Independent live-upstream capability matrix (not collected by pytest).

Requires the native SDK, curl, promtool and Go. Reports are external build artifacts.
GitHub Actions publishes the generated reports; no inventory or report is versioned.
"""
import argparse
from collections import Counter
import concurrent.futures
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.dont_write_bytecode = True
sys.path[:0] = [str(ROOT / "python/metricraft/src"), str(ROOT / "tests/conformance")]
from inventory import discover, snapshot
from probes import candidates
from cases import cases
from cases import experimental_cases
from extensions import cases as extension_cases, FEATURES
from topics import responsibility


def run(command, **kwargs):
    return subprocess.run(command, capture_output=True, text=True, encoding="utf-8", timeout=180, **kwargs)


def probe(row, signatures, syntax_cases):
    results = []
    for variant, make in candidates(row, signatures, syntax_cases):
        record = {"id": row["id"] + "/" + variant, "variant": variant}
        try:
            query = make()
        except (ValueError, TypeError) as exc:
            record.update(status="missing" if "not implemented" in str(exc) else "signature_gap", error=str(exc))
        else:
            try:
                text = query.build(row["mode"], experimental_functions=True, features=FEATURES)
            except ValueError as exc:
                record.update(status="dialect_gap", error=str(exc))
            else:
                record.update(status="built", query=text)
                try:
                    query.build(row["mode"])
                    record["requires_experimental_opt_in"] = False
                except ValueError as exc:
                    if not any(s in str(exc) for s in ("experimental_functions", "experimental feature", "requires features=")):
                        raise
                    record["requires_experimental_opt_in"] = True
        results.append(record)
    return results


def parse_queries(rows, output):
    by_mode = {mode: [p for r in rows if r["mode"] == mode for p in r["probes"] if p["status"] == "built"]
               for mode in ("promql", "metricsql")}
    # Always run both upstream parsers on a positive and negative control.
    controls = [{"query": "up", "expected": True}, {"query": "-1", "expected": True},
                {"query": "rate(", "expected": False}]

    def prom(record):
        command = ["promtool", "--experimental", "--enable-feature=promql-experimental-functions," + ",".join(FEATURES),
                   "promql", "format", "--", record["query"]]
        result = run(command)
        return result.returncode == 0, (result.stderr or result.stdout).strip()

    prom_records = controls + by_mode["promql"]
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
        prom_results = list(pool.map(prom, prom_records))
    for control, (ok, _) in zip(controls, prom_results):
        if ok != control["expected"]:
            raise RuntimeError("PromQL oracle control failed; verify promtool and its experimental command flag")
    for record, (ok, error) in zip(by_mode["promql"], prom_results[len(controls):]):
        record.update(status="parsed_witness" if ok else "parser_rejected", parser_error="" if ok else error)

    env = os.environ.copy()
    env.setdefault("GOCACHE", str(output.parent / "go-cache"))
    env.setdefault("GOMODCACHE", str(output.parent / "go-mod"))
    env.setdefault("GOTOOLCHAIN", "local")
    vm_queries = [p["query"] for p in controls + by_mode["metricsql"]]
    result = run(["go", "run", "-mod=readonly", ".", "--json"],
                 cwd=ROOT / "tests/conformance/metricsql", env=env, input=json.dumps(vm_queries))
    if result.returncode:
        raise RuntimeError("MetricsQL oracle failed: " + result.stderr)
    vm_results = json.loads(result.stdout)
    if len(vm_results) != len(vm_queries) or any(p["ok"] != c["expected"] for p, c in zip(vm_results, controls)):
        raise RuntimeError("MetricsQL oracle control/protocol failed")
    for record, parsed in zip(by_mode["metricsql"], vm_results[len(controls):]):
        record.update(status="parsed_witness" if parsed["ok"] else "parser_rejected", parser_error=parsed["error"])
    version = run(["promtool", "--version"])
    if version.returncode:
        raise RuntimeError("could not identify PromQL oracle")
    if not re.search(r"version 3\.15\.0\b", version.stdout + version.stderr):
        raise RuntimeError("this matrix baseline requires promtool 3.15.0; upgrade the baseline and CI together")
    return {"promql": (version.stdout + version.stderr).strip(),
            "metricsql": "github.com/VictoriaMetrics/metricsql v0.87.4",
            "experimental_functions": True, "positive_and_negative_controls": "passed"}


def row_status(probes):
    states = {p["status"] for p in probes}
    if not states:
        return "needs_probe"
    if states == {"parsed_witness"}:
        return "sampled"
    if "parser_rejected" in states:
        return "parser_rejected"
    if "parsed_witness" in states:
        return "partial"
    return next(iter(states)) if len(states) == 1 else "signature_gap"


def fingerprints(rows, sources):
    return {"schema": 1, "capabilities": {r["id"]: r["fingerprint"] for r in rows},
            "source_digests": {key: value["sha256"] for key, value in sources["sources"].items()},
            "parsed_probes": sorted(p["id"] for r in rows for p in r["probes"] if p["status"] == "parsed_witness")}


def changes(previous, current):
    old, new = previous["capabilities"], current["capabilities"]
    return {"added": sorted(new.keys() - old.keys()), "removed": sorted(old.keys() - new.keys()),
            "changed": sorted(k for k in new.keys() & old.keys() if new[k] != old[k]),
            "changed_sources": sorted(k for k, v in current["source_digests"].items()
                                      if previous.get("source_digests", {}).get(k) != v),
            "regressed_probes": sorted(set(previous["parsed_probes"]) - set(current["parsed_probes"]))}


def summary(report):
    lines = ["# Upstream compatibility matrix", "",
             "`sampled` means all listed witnesses built and parsed. It does not mean full language, overload, or evaluation support.",
             "Scope: Prometheus 3.15.0 and VictoriaMetrics 1.153.0. `upstream_ahead` tracks unreleased main-branch additions.",
             "`backend_owned` covers evaluation/storage policy; `canonical_output` covers source formatting. Unmatched topics fail the workflow.",
             "Parser witnesses do not prove values. The separate backend artifact checks executable signatures and independently calculated results.", "",
             "Snapshot: " + report["sources"]["fetched_at"], "",
             "| Dialect | Status | Capabilities |", "| --- | --- | ---: |"]
    for mode, counts in report["summary"].items():
        lines.extend("| {} | {} | {} |".format(mode, status, count) for status, count in sorted(counts.items()))
    lines += ["", "Full capability details, source provenance and parser output are in the workflow artifact."]
    return "\n".join(lines) + "\n"


def markdown(report):
    lines = [summary(report), "## Comparison with previous report", "", "```json", json.dumps(report["changes"], indent=2), "```",
              "", "## Capabilities", "", "| Dialect | Kind | Name or topic | Status | Parsed / attempted |",
              "| --- | --- | --- | --- | ---: |"]
    for row in report["rows"]:
        name = row.get("description", row["name"]).replace("|", "\\|").replace("\n", " ")
        if len(name) > 140:
            name = name[:137] + "..."
        count = sum(p["status"] == "parsed_witness" for p in row["probes"])
        lines.append("| {} | {} | {} | {} | {} / {} |".format(
            row["mode"], row["kind"], name, row["status"], count, len(row["probes"])))
    lines += ["", "## Probe failures and gaps", ""]
    for row in report["rows"]:
        if "responsibility_reason" in row:
            lines.append("- `{}`: {} — {}".format(row["id"], row["status"], row["responsibility_reason"]))
        for p in row["probes"]:
            if p["status"] not in ("parsed_witness", "missing"):
                lines.append("- `{}`: {} — {}".format(p["id"], p["status"], p.get("error", p.get("parser_error", "")).replace("\n", " ")))
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--offline", action="store_true", help="reuse the output directory's verified source snapshot")
    parser.add_argument("--compare", type=Path, help="compare with matrix.json downloaded from a previous Actions artifact")
    parser.add_argument("--check", action="store_true", help="with --compare, fail on upstream drift or lost passing probes")
    args = parser.parse_args()
    if args.check and args.compare is None:
        parser.error("--check requires --compare with a previous generated matrix.json")
    output = args.output.resolve()
    if output == ROOT or ROOT in output.parents:
        parser.error("--output must be outside the checkout; reports are generated artifacts")
    previous = None
    if args.compare:
        previous_report = json.loads(args.compare.read_text(encoding="utf-8"))
        if previous_report.get("schema") != 1 or any(r["status"] == "parser_rejected" for r in previous_report["rows"]):
            raise ValueError("comparison requires a successful schema-1 matrix report")
        previous = fingerprints(previous_report["rows"], previous_report["sources"])
    for tool in ("curl", "go", "promtool"):
        if shutil.which(tool) is None:
            raise RuntimeError(tool + " is required")
    output.mkdir(parents=True, exist_ok=True)
    print("Reading official capability sources...", flush=True)
    texts, sources = snapshot(output / "sources", args.offline)
    rows = discover(texts)
    signatures = {r["name"]: r for r in rows if r["mode"] == "promql" and r["kind"] == "function"}
    syntax_cases = {(mode, name): query for source in (cases, experimental_cases, extension_cases)
                    for name, query, mode in source()}
    for row in rows:
        scope = responsibility(row)
        row["probes"] = [] if scope else probe(row, signatures, syntax_cases)
        if scope:
            row["responsibility_status"], row["responsibility_reason"] = scope
        row["backend_semantics"] = "unverified"
    print("Checking {} discovered capabilities against upstream parsers...".format(len(rows)), flush=True)
    parsers = parse_queries(rows, output)
    for row in rows:
        row["status"] = row.get("responsibility_status") or row_status(row["probes"])
    current = fingerprints(rows, sources)
    delta = changes(previous, current) if previous is not None else {"comparison": "not requested"}
    from metricraft import _native
    native = Path(_native.lib._name)
    report = {"schema": 1, "sources": sources, "offline": args.offline, "parsers": parsers,
              "native_sha256": hashlib.sha256(native.read_bytes()).hexdigest(),
              "source_hashes": {str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
                                for base in (ROOT / "crates", ROOT / "python/metricraft/src", ROOT / "scripts/compatibility", ROOT / "tests/conformance")
                                for p in base.rglob("*") if p.suffix in (".rs", ".py", ".go")},
              "changes": delta, "summary": {mode: dict(Counter(r["status"] for r in rows if r["mode"] == mode))
                                             for mode in ("promql", "metricsql")}, "rows": rows}
    (output / "matrix.json").write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    (output / "matrix.md").write_text(markdown(report), encoding="utf-8")
    (output / "summary.md").write_text(summary(report), encoding="utf-8")
    print(json.dumps(report["summary"], indent=2))
    print("Reports: " + str(output / "matrix.json") + " and matrix.md")
    rejected = any(r["status"] not in ("sampled", "backend_owned", "canonical_output", "upstream_ahead") for r in rows)
    return int(rejected or (args.check and any(delta.values())))


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as exc:
        print("Compatibility check failed: " + str(exc), file=sys.stderr)
        sys.exit(2)
