"""SDK recipes for Actions reports. Official documentation is data, not Python to evaluate.

Function probes sample signatures; topic probes sample syntax. Neither proves
backend evaluation equivalence or full support for every documented overload.
"""
from metricraft import QueryBuilder as Q
from function_recipes import recipes as extension_recipes
from topics import witnesses


def values():
    a = Q.from_metric("metricraft_a")
    return {"Vector": a, "Vector2": Q.from_metric("metricraft_b"), "Matrix": a.range("5m"), "Scalar": 0.3, "String": "job"}


def function_args(row, prom_signatures):
    v = values()
    name = row["name"]
    if row["mode"] == "metricsql" and name in extension_recipes(v):
        for i, args in enumerate(extension_recipes(v)[name]):
            yield "recipe-" + str(i), args
        return
    signature = row if "args" in row else prom_signatures.get(name, {})
    if "args" in signature:
        args = [v[t] for t in signature["args"]]
        if name == "label_replace":
            args = [v["Vector"], "dst", "$1", "src", "(.*)"]
        if name == "histogram_fraction":
            args = [0, 1, v["Vector"]]
        if name == "info":
            args = [v["Vector"], Q.from_labels(job="api")]
        if name == "histogram_quantiles":
            args = [v["Vector"], "phi", 0.5, 0.9]
        yield "declared", args
        if name == "histogram_quantiles" and row["mode"] == "promql":
            yield "maximum-arity", args[:2] + [i / 10 for i in range(1, 11)]
        variadic = signature.get("variadic", 0)
        if variadic:
            yield "minimum-arity", args[:-1]
            if variadic == -1 and args:
                yield "extra-argument", args + [args[-1]]
        return
    recipes = {
        "alias": [[v["Vector"], 'renamed"\\metric']],
        "union": [[], [v["Vector"]], [v["Vector"], v["Vector2"]]],
        "rollup": [[v["Matrix"]], [v["Matrix"], "max"]],
        "rollup_rate": [[v["Matrix"]], [v["Matrix"], "max"]],
        "holt_winters": [[v["Matrix"], 0.3, 0.3]],
        "smooth_exponential": [[v["Vector"], 0.3]],
        "label_set": [[v["Vector"]], [v["Vector"], "job", 'api"\\prod']],
        "label_del": [[v["Vector"]], [v["Vector"], "job"]],
        "label_keep": [[v["Vector"]], [v["Vector"], "job"]],
        "label_copy": [[v["Vector"]], [v["Vector"], "job", "service", "job", "owner"]],
        "label_move": [[v["Vector"]], [v["Vector"], "job", "service", "service", "owner"]],
        "label_map": [[v["Vector"], "job"], [v["Vector"], "job", "api", "web", "worker", "batch"]],
        "label_lowercase": [[v["Vector"], "job"], [v["Vector"], "job", "instance"]],
        "label_uppercase": [[v["Vector"], "job"], [v["Vector"], "job", "instance"]],
        "label_match": [[v["Vector"], "job", "api|worker"]],
        "label_mismatch": [[v["Vector"], "job", "test.*"]],
        "label_transform": [[v["Vector"], "job", "(api)", "$1-prod"]],
        "label_value": [[v["Vector"], "shard"]],
        "labels_equal": [[v["Vector"], "job", "service"], [v["Vector"], "job", "service", "owner"]],
        "label_graphite_group": [[v["Vector"], 0], [v["Vector"], 0, 2]],
        "drop_common_labels": [[v["Vector"]], [v["Vector"], v["Vector2"]]],
        "sort_by_label_numeric": [[v["Vector"], "job", "instance"]],
        "sort_by_label_numeric_desc": [[v["Vector"], "job", "instance"]],
    }
    if name in recipes:
        for i, args in enumerate(recipes[name]):
            yield "recipe-" + str(i), args
    elif row.get("category") == "Rollup functions":
        yield "range-witness", [v["Matrix"]]
    else:
        # A rejected empty call distinguishes missing names from missing probe signatures.
        yield "zero-argument-witness", []


def aggregate_args(name):
    a = values()["Vector"]
    if name in ("topk", "bottomk", "outliersk", "limitk", "outliers_mad") or name.startswith(("topk_", "bottomk_")):
        return [Q.from_scalar(3), a]
    if name in ("quantile", "limit_ratio"):
        return [Q.from_scalar(0.3), a]
    if name == "count_values":
        return [Q.from_string("value"), a]
    if name == "quantiles":
        return [Q.from_string("phi"), Q.from_scalar(0.5), Q.from_scalar(0.9), a]
    return [a]


def candidates(row, prom_signatures, syntax_cases):
    if row["kind"] == "function":
        for variant, args in function_args(row, prom_signatures):
            yield variant, lambda args=args: Q.function(row["name"], *args)
    elif row["kind"] == "aggregate":
        args = aggregate_args(row["name"])
        for grouping in ("plain", "by", "without"):
            def make(grouping=grouping):
                q = Q._apply(row["name"], children=args)
                return q if grouping == "plain" else getattr(q, grouping)("job")
            yield grouping, make
        if row["mode"] == "metricsql":
            if row["name"].startswith(("topk_", "bottomk_")):
                yield "remaining-series", lambda: Q._apply(row["name"], children=args + [Q.from_string("remaining=other")])
            elif len(args) == 1:
                if row["name"] != "outliers_iqr":
                    yield "variadic-vectors", lambda: Q._apply(row["name"], children=args + [Q.from_metric("metricraft_b")])
                yield "implicit-scalar", lambda: Q._apply(row["name"], children=[Q.from_scalar(1)])
    elif row["kind"] == "operator":
        yield "vector-vector", lambda: Q._apply(row["name"], children=(Q.from_metric("a"), Q.from_metric("b")))
    else:
        for name in topic_cases(row):
            query = syntax_cases.get((row["mode"], name))
            if query is not None:
                yield name, lambda query=query: query


def topic_cases(row):
    mapping = {
        "prom-basics/string-literals": ["label_replace"],
        "prom-basics/float-literals-and-time-durations": ["scalar", "subquery"],
        "prom-basics/instant-vector-selectors": ["selector", "regex", "same_label_conjunction", "unnamed_selector"],
        "prom-basics/range-vector-selectors": ["rate"],
        "prom-basics/offset-modifier": ["offset", "negative_offset"],
        "prom-basics/-modifier": ["at_timestamp", "at_start", "at_end"],
        "prom-basics/subquery": ["subquery", "subquery_default_step", "subquery_offset"],
        "prom-basics/regular-expressions": ["regex"],
        "prom-operators/unary-operator": ["negate", "positive"],
        "prom-operators/arithmetic-binary-operators": ["arithmetic", "power"],
        "prom-operators/trigonometric-binary-operators": ["atan2"],
        "prom-operators/comparison-binary-operators": ["comparison", "comparison_bool", "scalar_comparison"],
        "prom-operators/logicalset-binary-operators": ["set_and", "set_or", "set_unless"],
        "prom-operators/vector-matching-keywords": ["matching", "matching_bool", "empty_matching"],
        "prom-operators/group-modifiers": ["matching", "matching_bool"],
        "prom-operators/one-to-one-vector-matches": ["set_and"],
        "prom-operators/many-to-one-and-one-to-many-vector-matches": ["matching", "matching_bool"],
        "prom-operators/binary-operator-precedence": ["arithmetic"],
        "keep_metric_names": ["keep_names", "keep_binary_names"],
        "subqueries": ["subquery", "implicit_subquery"],
    }
    if row["kind"] == "topic":
        return mapping.get(row["name"], witnesses(row))
    description = row.get("description", "")
    for prefix, names in (
        ("The lookbehind window in square brackets", ["implicit_range"]),
        ("`default` binary operator.", ["default"]),
        ("`if` binary operator.", ["if"]),
        ("`ifnot` binary operator.", ["ifnot"]),
        ("`keep_metric_names` modifier", ["keep_names", "keep_binary_names"]),
    ):
        if description.startswith(prefix):
            return names
    return witnesses(row)
