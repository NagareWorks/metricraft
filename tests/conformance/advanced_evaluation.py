"""Independent result witnesses for language extensions; no upstream discovery."""
import math

from metricraft import QueryBuilder as Q
from evaluation import Case, jobs


def cases(index):
    a = Q.from_metric("mc_temperature")
    totals = a.sum().by("job")
    limits = Q.from_metric("mc_limit")
    missing = Q.from_metric("mc_missing")
    x = Q.reference("x")
    f = Q.template("x", body=x.sum().by("job"))
    prefix = Q.reference("prefix", kind="string")
    histogram = Q.from_metric("mc_duration_seconds_bucket").rate("5m").sum().by("job", "le")
    common = [
        Case("portable_histogram_quantiles", histogram.histogram_quantiles("phi", 0.5, 0.9),
             [({"job": "api", "phi": "0.5"}, 0.4), ({"job": "api", "phi": "0.9"}, 1)],
             experimental_functions=True),
        Case("first_over_time", limits.first_over_time("5m").sum().by("job"), jobs(100, 10)),
    ]
    vm = [
        ("with_value", (x + 1).with_(x=totals), jobs(3 * index + 1, 11)),
        ("with_function", Q.template_call("f", a).with_(f=f), jobs(3 * index, 10)),
        ("with_string_filter", a.where_eq("job", prefix + "pi").sum().by("job").with_(prefix="a"), [({"job": "api"}, 3 * index)]),
        ("selector_alternatives", a.where_eq("job", "api").or_selector(a.where_eq("job", "worker")).sum().by("job"), jobs(3 * index, 10)),
        ("selector_common_filter", a.where_eq("job", "api").or_selector(a.where_eq("job", "worker")).where_eq("job", "api").sum().by("job"), [({"job": "api"}, 3 * index)]),
        ("scalar_aggregate", Q.from_scalar(2).sum(), [({}, 2)]),
        ("tuple_filter", totals.eq_any(24, 27, 30, 10), jobs(3 * index, 10)),
        ("aggregate_limit", totals.limit(1).count(), [({}, 1)]),
        ("variadic_aggregate", a.avg(a * 2).by("job"), jobs(2.25 * index, 15)),
        ("sum2", a.sum2().by("job"), jobs(5 * index ** 2, 100)),
        ("geomean", a.geomean().by("job"), jobs(math.sqrt(2) * index, 10)),
        ("bitmap", totals.bitmap_and(3), jobs((3 * index) & 3, 10 & 3)),
        ("group_prefix", (totals / limits).on("job").group_left_all(prefix="source_"),
         [({"job": "api", "source_team": "core"}, 3 * index / 100), ({"job": "worker", "source_team": "batch"}, 1)]),
    ]
    prom = [
        Case("fill_missing", (totals + missing).fill_right(0), jobs(3 * index, 10),
             ("promql",), features=("promql-binop-fill-modifiers",)),
        Case("anchored_rate", Q.from_metric("mc_requests_total").range("5m").anchored().rate().sum().by("job"),
             jobs(15, 3), ("promql",), features=("promql-extended-range-selectors",)),
        Case("smoothed_rate", Q.from_metric("mc_requests_total").range("5m").smoothed().offset("1m").rate().sum().by("job"),
             jobs(15, 3), ("promql",), features=("promql-extended-range-selectors",)),
        Case("duration_range", limits.subquery(Q.query_range().max_of(300), Q.step().max_of(60)).avg_over_time().sum().by("job"),
             jobs(100, 10), ("promql",), range_check=True, features=("promql-duration-expr",)),
    ]
    return common + [Case("vm_" + name, query, expected, ("metricsql",), range_check=True)
                     for name, query, expected in vm] + prom
