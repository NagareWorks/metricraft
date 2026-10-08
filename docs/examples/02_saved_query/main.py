"""Application-owned persistence and a client accepting loaded query text."""

import argparse
import sqlite3

from metricraft import QueryBuilder as Q
from metricraft.config.http_options import HttpClientOptions
from metricraft import DatabaseClient, VMSingleConfig


class DemoTransport:
    """Offline transport so the default example needs no VictoriaMetrics server."""

    def get(self, url, params=None):
        assert params["query"] == "sum by (job) (rate(http_requests_total[5m]))"
        return {"status": "success", "data": {"resultType": "vector", "result": []}}

    def close(self):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--database", default=":memory:", help="Application-owned SQLite path"
    )
    parser.add_argument(
        "--url",
        help="Optional VictoriaMetrics single-node URL; omit for offline execution",
    )
    args = parser.parse_args()
    text = (
        Q.from_metric("http_requests_total").rate("5m").sum().by("job").build("promql")
    )

    # Persistence belongs to this application. MetriCraft only returns a string.
    connection = sqlite3.connect(args.database)
    try:
        with connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS saved_queries (name TEXT PRIMARY KEY, query TEXT)"
            )
            connection.execute(
                "INSERT OR REPLACE INTO saved_queries VALUES (?, ?)",
                ("request_rate", text),
            )
        loaded = connection.execute(
            "SELECT query FROM saved_queries WHERE name = ?", ("request_rate",)
        ).fetchone()[0]
    finally:
        connection.close()

    if args.url:
        config = VMSingleConfig(args.url)
    else:
        config = VMSingleConfig(
            "http://example.invalid",
            http_options=HttpClientOptions(client=DemoTransport()),
        )
    with DatabaseClient(config) as client:
        result = client.query(loaded)
        assert result.is_success
        print(loaded)
        print(
            "Query succeeded (real backend)."
            if args.url
            else "Query succeeded (offline transport)."
        )


if __name__ == "__main__":
    main()
