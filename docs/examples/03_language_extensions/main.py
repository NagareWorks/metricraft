"""Offline construction; applications own storage and execution."""
from metricraft import QueryBuilder as Q


def main():
    base = Q.from_metric("http_requests_total").where_eq("env", "prod")
    api = base.where_eq("job", "api")
    worker = base.where_eq("job", "worker")
    print(api.or_selector(worker).rate("5i").sum().by("job").limit(10).build("metricsql"))

    parameter = Q.reference("series")
    per_job = Q.template("series", body=parameter.rate("5m").sum().by("job"))
    query = Q.template_call("per_job", base).with_(per_job=per_job)
    print(query.build("metricsql"))

    prefix = Q.reference("prefix", kind="string")
    filtered = Q.from_labels().where_eq("__name__", prefix + "requests_total")
    print(filtered.with_(prefix="http_").build("metricsql"))

    portable = base.rate("5m").sum().by("job")
    assert portable.build("promql") == portable.build("metricsql")
    assert base.build("promql") == 'http_requests_total{env="prod"}'
    print(base.range(Q.step().max_of(60) * 2).rate().build(
        "promql", features=("promql-duration-expr",)))


if __name__ == "__main__":
    main()
