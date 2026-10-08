"""Application-side mapping from UI selections to a query string. No server."""

from metricraft import QueryBuilder as Q

# These allowlists are application policy, not SDK configuration.
METRICS = {"requests": "http_requests_total"}
WINDOWS = {"5m", "15m", "1h"}
LABELS = {"job", "instance"}


def build_query(selection):
    metric = METRICS[selection["metric"]]
    window = selection["window"]
    if window not in WINDOWS:
        raise ValueError("window is not allowed")
    query = Q.from_metric(metric)
    for label, value in selection.get("equals", {}).items():
        if label not in LABELS:
            raise ValueError("label is not allowed")
        query = query.where_eq(label, value)
    return query.rate(window).sum().by("job").build(mode="promql")


if __name__ == "__main__":
    # This dictionary could come from a validated request in your own application.
    text = build_query({"metric": "requests", "window": "5m", "equals": {"job": "api"}})
    assert text == 'sum by (job) (rate(http_requests_total{job="api"}[5m]))'
    print(text)
