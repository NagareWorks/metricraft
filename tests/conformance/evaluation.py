"""Synthetic backend fixtures and independently calculated result expectations.

These are integration witnesses, not a language coverage inventory or unit tests.
"""
from dataclasses import dataclass

from metricraft import QueryBuilder as Q


ESCAPED = 'quote" slash\\ newline\n中'


def series():
    """Eleven one-minute samples; counters are linear and gauges vary with time."""
    rows = []

    def add(name, labels, values):
        rows.append({"metric": dict(__name__=name, **labels), "values": values})

    for job, instance, status, increment in (
        ("api", "a", "200", 540), ("api", "a", "500", 60),
        ("api", "b", "200", 240), ("api", "b", "500", 60),
        ("worker", "c", "200", 180),
    ):
        add("mc_requests_total", dict(job=job, instance=instance, status=status),
            [increment * i for i in range(11)])
    for bound, increment in (("0.1", 60), ("0.5", 180), ("1", 270), ("+Inf", 300)):
        add("mc_duration_seconds_bucket", dict(job="api", le=bound),
            [increment * i for i in range(11)])
    for job, instance, factor in (("api", "a", 1), ("api", "b", 2), ("worker", "c", 0)):
        add("mc_temperature", dict(job=job, instance=instance),
            [factor * i if factor else 10 for i in range(11)])
    add("mc_limit", dict(job="api", team="core"), [100] * 11)
    add("mc_limit", dict(job="worker", team="batch"), [10] * 11)
    add("mc_escaped", dict(note=ESCAPED), [7] * 11)
    return rows


@dataclass(frozen=True)
class Case:
    name: str
    query: object
    expected: list
    modes: tuple = ("promql", "metricsql")
    range_check: bool = False
    experimental_functions: bool = False
    features: tuple = ()


def jobs(api, worker):
    return [({"job": "api"}, api), ({"job": "worker"}, worker)]


def cases(start, index=10):
    from advanced_evaluation import cases as advanced_cases
    requests = Q.from_metric("mc_requests_total")
    rates = requests.rate("5m").sum().by("job")
    errors = requests.where_regex("status", "5..").rate("5m").sum().by("job")
    temperature = Q.from_metric("mc_temperature")
    totals = temperature.sum().by("job")
    missing = Q.from_metric("mc_missing")
    limits = Q.from_metric("mc_limit")
    return [
        Case("sum_by", totals, jobs(3 * index, 10), range_check=True),
        Case("sum_without", temperature.sum().without("instance"), jobs(3 * index, 10)),
        Case("ungrouped_sum", temperature.sum(), [({}, 3 * index + 10)]),
        Case("rate_by", rates, jobs(15, 3), range_check=True),
        Case("error_ratio", 100 * errors / rates, [({"job": "api"}, 100 * 2 / 15)]),
        Case("increase", requests.increase("5m").sum().by("job"), jobs(4500, 900)),
        Case("histogram_quantile", Q.from_metric("mc_duration_seconds_bucket").rate("5m")
             .sum().by("job", "le").histogram_quantile(0.9), [({"job": "api"}, 1)]),
        Case("comparison_bool", totals.gt(25).bool(), jobs(int(3 * index > 25), 0)),
        Case("comparison_filter", totals.gt(25), [({"job": "api"}, 3 * index)] if 3 * index > 25 else []),
        Case("group_left", (totals / limits).on("job").group_left("team"),
             [({"job": "api", "team": "core"}, 3 * index / 100),
              ({"job": "worker", "team": "batch"}, 1)]),
        Case("set_and", totals.and_(errors).on("job"), [({"job": "api"}, 3 * index)]),
        Case("set_unless", totals.unless(errors).on("job"), [({"job": "worker"}, 10)]),
        Case("set_or", totals.or_(errors).on("job"), jobs(3 * index, 10)),
        Case("offset", temperature.offset("2m").sum().by("job"), jobs(3 * (index - 2), 10)),
        Case("fixed_at", temperature.at(start + 7 * 60).sum().by("job"), jobs(21, 10), range_check=True),
        Case("subquery", rates.subquery("4m", "1m").avg_over_time(), jobs(15, 3)),
        Case("clamp", totals.clamp(12, 25), jobs(min(25, max(12, 3 * index)), 12)),
        Case("escaped_selector", Q.from_metric("mc_escaped").where_eq("note", ESCAPED).sum(), [({}, 7)]),
        Case("missing_series", missing, []),
        Case("scalar_arithmetic", (Q.from_scalar(2) + 3 * Q.from_scalar(4)).vector(), [({}, 14)]),
        Case("vm_default", missing.default(totals), jobs(3 * index, 10), ("metricsql",)),
        Case("vm_if", totals.if_(errors).on("job"), [({"job": "api"}, 3 * index)], ("metricsql",)),
        Case("vm_ifnot", totals.ifnot(errors).on("job"), [({"job": "worker"}, 10)], ("metricsql",)),
        Case("vm_union", totals.union(errors), jobs(3 * index, 10), ("metricsql",)),
    ] + label_cases(totals, index) + advanced_cases(index)


def label_cases(totals, index):
    """VM label witnesses include ordering, absent labels and nonnumeric values."""
    api, worker = 3 * index, 10
    numbered = totals.label_copy(("job", "shard")).label_map(
        "shard", ("api", "2"), ("worker", "not-a-number")
    )
    witnesses = [
        ("vm_label_copy", totals.label_copy(("job", "service"), ("job", "owner")),
         [({"job": "api", "service": "api", "owner": "api"}, api),
          ({"job": "worker", "service": "worker", "owner": "worker"}, worker)]),
        ("vm_label_move", totals.label_move(("job", "service"), ("service", "owner")),
         [({"owner": "api"}, api), ({"owner": "worker"}, worker)]),
        ("vm_label_copy_missing", totals.label_copy(("missing", "job")), jobs(api, worker)),
        ("vm_label_move_missing", totals.label_move(("missing", "job")), jobs(api, worker)),
        ("vm_label_move_self", totals.label_move(("job", "job")), jobs(api, worker)),
        ("vm_label_copy_empty", totals.label_copy(), jobs(api, worker)),
        ("vm_label_move_empty", totals.label_move(), jobs(api, worker)),
        ("vm_label_map_empty", totals.label_map("job"), jobs(api, worker)),
        ("vm_label_map", totals.label_map("job", ("api", ESCAPED), ("worker", "batch")),
         [({"job": ESCAPED}, api), ({"job": "batch"}, worker)]),
        ("vm_label_map_remove", totals.label_map("job", ("api", "")),
         [({}, api), ({"job": "worker"}, worker)]),
        ("vm_label_uppercase", totals.label_uppercase("job"),
         [({"job": "API"}, api), ({"job": "WORKER"}, worker)]),
        ("vm_label_lowercase", totals.label_set(zone="EAST").label_lowercase("job", "zone"),
         [({"job": "api", "zone": "east"}, api), ({"job": "worker", "zone": "east"}, worker)]),
        ("vm_label_match", totals.label_match("job", "api"), [({"job": "api"}, api)]),
        ("vm_label_match_anchored", totals.label_match("job", "pi"), []),
        ("vm_label_mismatch", totals.label_mismatch("job", "api"), [({"job": "worker"}, worker)]),
        ("vm_label_match_missing", totals.label_match("missing", ""), jobs(api, worker)),
        ("vm_label_transform", totals.label_transform("job", "(r)", "${1}X"),
         [({"job": "api"}, api), ({"job": "worXkerX"}, worker)]),
        ("vm_label_value", numbered.label_value("shard"), [({"job": "api", "shard": "2"}, 2)]),
        ("vm_labels_equal", totals.label_set(service="api").labels_equal("job", "service"),
         [({"job": "api", "service": "api"}, api)]),
        ("vm_labels_equal_missing", totals.labels_equal("missing", "absent"), jobs(api, worker)),
        ("vm_label_graphite_group", totals.alias("servers.api.requests").label_graphite_group(0, 2),
         [({"__name__": "servers.requests", "job": "api"}, api),
          ({"__name__": "servers.requests", "job": "worker"}, worker)]),
        ("vm_drop_common_labels", totals.label_set(env="prod").drop_common_labels(), jobs(api, worker)),
        ("vm_drop_common_labels_multiple",
         totals.label_match("job", "api").label_set(env="prod").drop_common_labels(
             totals.label_match("job", "worker").label_set(env="prod")), jobs(api, worker)),
    ]
    return [Case(name, query, expected, ("metricsql",),
                 range_check=name in {"vm_label_copy", "vm_label_value", "vm_drop_common_labels"})
            for name, query, expected in witnesses]
