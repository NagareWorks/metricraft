import pytest
from metricraft import QueryBuilder


def test_codegen_smoke_complex():
    q = (
        QueryBuilder.from_metric("a")
        .where_eq("job", "x")
        .range("5m")
        .rate()
        .keep_metric_names()
        .sum().by("job")
    )
    assert (
        q.build("metricsql") == 'sum by (job) (rate(a{job="x"}[5m]) keep_metric_names)'
    )
    with pytest.raises(ValueError, match="MetricsQL-only"):
        q.build("promql")
