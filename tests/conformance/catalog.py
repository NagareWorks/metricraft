"""Backend acceptance for the independently generated upstream matrix artifact.

Acceptance establishes executable signatures, not numerical equivalence. Value
and label expectations live in evaluation.py and are reported separately.
"""
import json


def evaluate(client, mode, start, matrix, report):
    if matrix is None:
        return
    inventory = json.loads(matrix.read_text(encoding="utf-8"))
    if inventory.get("schema") != 1:
        raise ValueError("unsupported compatibility matrix schema")
    attempted = 0
    failed = []
    for row in inventory["rows"]:
        if row["mode"] != mode or row["kind"] not in ("function", "aggregate", "operator", "feature", "topic"):
            continue
        if row.get("in_prometheus_baseline_catalog") is False:
            continue
        for probe in row["probes"]:
            if probe["status"] != "parsed_witness":
                continue
            attempted += 1
            item = {"id": probe["id"], "mode": mode, "query": probe["query"], "status": "failed"}
            report.setdefault("catalog", []).append(item)
            try:
                result = client.query(probe["query"], time=start + 600)
                if not result.is_success or result.is_partial:
                    raise AssertionError("backend rejected instant query: " + repr(result))
                item["instant_result_type"] = result.result_type
                if result.result_type in ("vector", "scalar"):
                    result = client.query_range(probe["query"], start=start + 480, end=start + 600, step="60s")
                    if not result.is_success or result.is_partial:
                        raise AssertionError("backend rejected range query: " + repr(result))
                    item["range_result_type"] = result.result_type
                item["status"] = "accepted"
            except Exception as exc:
                item["error"] = str(exc)
                failed.append(item["id"] + ": " + str(exc))
    if attempted == 0:
        raise AssertionError("catalog acceptance needs at least one generated probe")
    report.setdefault("catalog_failures", []).extend(failed)
