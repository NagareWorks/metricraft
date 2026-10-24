"""Every marked line must fail; this file is never executed."""
from typing import Mapping
from metricraft.client import SyncHTTPClient
from metricraft import HttpClientOptions, SyncHTTPTransport, DatabaseClient, PrometheusConfig, QueryBuilder as Q

base = Q.from_metric("up")
Q.from_metric(123)  # expect: arg-type
base.where_eq("job", 123)  # expect: arg-type
base.where("job", "contains", "api")  # expect: arg-type
base.rate(300)  # expect: arg-type
base.sum().by(123)  # expect: arg-type
base.topk("three")  # expect: arg-type
base.default([])  # expect: arg-type
base.label_copy(("source", 123))  # expect: arg-type
base.build("sql")  # expect: arg-type
base.build(max_output_bytes="large")  # expect: arg-type
Q.reference("x", kind="unknown")  # expect: arg-type
Q.template("x", body=[])  # expect: arg-type
base.sum().misspelled()  # expect: attr-defined
query: str = base.sum()  # expect: assignment
DatabaseClient(PrometheusConfig("http://localhost:9090")).query(123)  # expect: arg-type
bad_selectors = [123]
DatabaseClient(PrometheusConfig("http://localhost:9090")).series(bad_selectors)  # expect: arg-type


class IncompleteTransport:
    def get(self, url: str) -> str:
        return "raw response"


def bad_factory(options: Mapping[str, object]) -> SyncHTTPTransport:
    raise NotImplementedError


HttpClientOptions(client=IncompleteTransport())  # expect: arg-type
HttpClientOptions(async_client=IncompleteTransport())  # expect: arg-type
HttpClientOptions(client_factory=bad_factory)  # expect: arg-type
HttpClientOptions(async_client_factory=bad_factory)  # expect: arg-type

HttpClientOptions(async_client=SyncHTTPClient())  # expect: arg-type

SyncHTTPClient().get("http://localhost:9090", params={1: "up"})  # expect: dict-item
