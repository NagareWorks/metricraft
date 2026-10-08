"""Check generated expressions with installed promtool and a pinned MetricsQL parser."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "python/metricraft/src"), str(ROOT / "tests/conformance")]
from cases import cases, experimental_cases
from migration import parser_cases
from extensions import cases as extension_cases, FEATURES


def main():
    for tool in ("promtool", "go"):
        if shutil.which(tool) is None:
            raise SystemExit(tool + " is required for upstream parser conformance")
    target = Path(os.environ.get("CARGO_TARGET_DIR", ROOT / "target")).resolve()
    artifacts = target.parent / "parser-conformance"
    artifacts.mkdir(parents=True, exist_ok=True)
    generated = [(name, query.build(mode), mode) for name, query, mode in cases()]
    generated.extend((name, query.build(mode, experimental_functions=True), mode)
                     for name, query, mode in experimental_cases())
    generated.extend((name, query.build(mode, experimental_functions=True), mode)
                     for name, query, mode in parser_cases())
    generated.extend(("extension_" + name, query.build(mode, experimental_functions=True, features=FEATURES), mode)
                     for name, query, mode in extension_cases())
    prometheus = [
        {"record": "metricraft_case_" + name, "expr": text}
        for name, text, mode in generated
        if mode == "promql"
    ]
    metricsql = [text for _, text, mode in generated if mode == "metricsql"]
    env = os.environ.copy()
    env.setdefault("GOCACHE", str(target.parent / "go-cache"))
    env.setdefault("GOMODCACHE", str(target.parent / "go-mod"))
    env.setdefault("GOTOOLCHAIN", "local")
    with tempfile.TemporaryDirectory(dir=artifacts) as directory:
        rules = Path(directory) / "rules.yaml"
        rules.write_text(
            json.dumps({"groups": [{"name": "generated", "rules": prometheus}]}),
            encoding="utf-8",
        )
        subprocess.run(["promtool", "--version"], check=True)
        subprocess.run(
            ["promtool", "--enable-feature=promql-experimental-functions," + ",".join(FEATURES), "check", "rules", "--lint=none", str(rules)], check=True
        )
    subprocess.run(
        ["go", "run", "-mod=readonly", "."],
        cwd=ROOT / "tests/conformance/metricsql",
        input=json.dumps(metricsql),
        text=True,
        env=env,
        check=True,
    )
    print(
        "Upstream parser conformance passed: {} PromQL, {} MetricsQL cases.".format(
            len(prometheus), len(metricsql)
        )
    )


if __name__ == "__main__":
    main()
