"""Discover upstream capabilities for generated Actions reports; never execute source data."""
import concurrent.futures
import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone

SOURCES = {
    "prom-signatures": "https://raw.githubusercontent.com/prometheus/prometheus/main/promql/parser/functions.go",
    "prom-baseline-signatures": "https://raw.githubusercontent.com/prometheus/prometheus/v3.15.0/promql/parser/functions.go",
    "prom-functions": "https://raw.githubusercontent.com/prometheus/prometheus/main/docs/querying/functions.md",
    "prom-operators": "https://raw.githubusercontent.com/prometheus/prometheus/main/docs/querying/operators.md",
    "prom-basics": "https://raw.githubusercontent.com/prometheus/prometheus/main/docs/querying/basics.md",
    "metricsql": "https://raw.githubusercontent.com/VictoriaMetrics/VictoriaMetrics/master/docs/victoriametrics/MetricsQL.md",
}


def digest(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def snapshot(directory, offline=False):
    """An explicit offline run reuses a verified snapshot; refresh never silently falls back."""
    directory.mkdir(parents=True, exist_ok=True)
    manifest_path = directory / "sources.json"
    if offline:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        texts = {}
        for key, url in SOURCES.items():
            text = (directory / (key + ".txt")).read_text(encoding="utf-8")
            if manifest["sources"][key]["url"] != url or digest(text) != manifest["sources"][key]["sha256"]:
                raise ValueError("snapshot provenance/hash mismatch: " + key)
            texts[key] = text
        return texts, manifest

    def fetch(item):
        key, url = item
        result = subprocess.run(
            ["curl", "--fail", "--silent", "--show-error", "--location", "--retry", "2",
             "--connect-timeout", "10", "--max-time", "40", url],
            capture_output=True, check=True, timeout=150,
        )
        if not result.stdout or len(result.stdout) > 4 * 1024 * 1024:
            raise ValueError("unexpected upstream document size: " + key)
        return key, result.stdout.decode("utf-8").replace("\r\n", "\n")

    with concurrent.futures.ThreadPoolExecutor(max_workers=len(SOURCES)) as pool:
        texts = dict(pool.map(fetch, SOURCES.items()))
    # Validate extraction before replacing any previously usable snapshot.
    discover(texts)
    manifest = {"fetched_at": datetime.now(timezone.utc).isoformat(), "sources": {
        key: {"url": SOURCES[key], "sha256": digest(text)} for key, text in texts.items()
    }}
    for key, text in texts.items():
        (directory / (key + ".txt")).write_text(text, encoding="utf-8")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return texts, manifest


def slug(title):
    return re.sub(r"[^\w -]", "", title.lower()).replace(" ", "-")


def sections(markdown):
    # Ignore headings and list items inside fenced examples.
    markdown = re.sub(r"(?ms)^(`{3,}|~{3,})[^\n]*\n.*?^\1[^\n]*$", "", markdown)
    matches = list(re.finditer(r"(?m)^(#{2,6}) (.+)$", markdown))
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(markdown)
        yield len(match[1]), match[2], markdown[match.end():end]


def discover(texts):
    rows = []

    def add(mode, kind, name, source, evidence, **metadata):
        rows.append(dict(id=mode + ":" + kind + ":" + name, mode=mode, kind=kind, name=name,
                         source=source, fingerprint=digest(evidence), **metadata))

    signatures = re.findall(r'(?ms)^\t"([a-z][a-z0-9_]*)": \{\n(.*?)^\t\},', texts["prom-signatures"])
    baseline_names = set(re.findall(r'(?m)^\t"([a-z][a-z0-9_]*)": \{', texts["prom-baseline-signatures"]))
    if len(baseline_names) < 60:
        raise ValueError("pinned Prometheus function catalog extraction failed")
    for name, body in signatures:
        types = re.search(r"ArgTypes:\s*\[\]ValueType\{([^}]*)\}", body)
        returns = re.search(r"ReturnType:\s*ValueType(\w+)", body)
        if not types or not returns:
            raise ValueError("unrecognized PromQL signature: " + name)
        args = re.findall(r"ValueType(\w+)", types[1])
        variadic = re.search(r"Variadic:\s*(-?\d+)", body)
        add("promql", "function", name, "prom-signatures", body, args=args,
            variadic=int(variadic[1]) if variadic else 0,
            experimental=bool(re.search(r"Experimental:\s*true", body)), returns=returns[1],
            in_prometheus_baseline_catalog=name in baseline_names)

    # Function headings are a second source: documentation-only additions stay visible.
    known = {row["name"] for row in rows}
    for _, title, body in sections(texts["prom-functions"]):
        for name in re.findall(r"`([a-z][a-z0-9_]*)\(\)`", title):
            if name not in known:
                add("promql", "function", name, "prom-functions", title + body)
                known.add(name)
    for source in ("prom-basics", "prom-operators"):
        parents = {}
        for level, title, body in sections(texts[source]):
            parents = {depth: path for depth, path in parents.items() if depth < level}
            path = slug(title)
            if level > 3 and parents:
                path = parents[max(parents)] + "/" + path
            parents[level] = path
            add("promql", "topic", source + "/" + path, source, title + body, title=title)
            if title == "Aggregation operators":
                for name in re.findall(r"(?m)^\* `([a-z_]+)\(", body):
                    add("promql", "aggregate", name, source, name)
            if title in ("Arithmetic binary operators", "Trigonometric binary operators",
                         "Comparison binary operators", "Logical/set binary operators", "Histogram trim operators"):
                for op in re.findall(r"(?m)^\* `([^`]+)`", body):
                    add("promql", "operator", op, source, op)

    category = ""
    introduction = texts["metricsql"].split("\n## ", 1)[0]
    for bullet in re.split(r"(?m)^\* ", introduction)[1:]:
        normalized = " ".join(bullet.split())
        add("metricsql", "semantic_difference", digest(normalized)[:16], "metricsql", normalized,
            description=normalized)
    for level, title, body in sections(texts["metricsql"]):
        if level == 3:
            category = title
        if level == 4 and re.fullmatch(r"[a-z][a-z0-9_]*", title):
            kind = "aggregate" if category == "Aggregate functions" else "function"
            add("metricsql", kind, title, "metricsql", title + body, category=category,
                documented_signatures=re.findall(r"`(" + title + r"\([^`]+\))`", body))
        elif level <= 3:
            add("metricsql", "topic", slug(title), "metricsql", title + body, title=title)
        if title == "MetricsQL features":
            bullets = re.split(r"(?m)^\* ", body)[1:]
            for bullet in bullets:
                # A content-addressed item makes new/edited prose visible instead of guessing semantics.
                normalized = " ".join(bullet.split())
                add("metricsql", "feature", digest(normalized)[:16], "metricsql", normalized,
                    description=normalized)
    ids = [r["id"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate upstream capability IDs")
    counts = {mode: sum(r["kind"] == "function" and r["mode"] == mode for r in rows)
              for mode in ("promql", "metricsql")}
    if counts["promql"] < 60 or counts["metricsql"] < 150:
        raise ValueError("upstream extraction unexpectedly sparse: " + str(counts))
    if not any(r["kind"] == "feature" for r in rows):
        raise ValueError("MetricsQL feature extraction returned no items")
    return sorted(rows, key=lambda row: row["id"])
