# Configurable query contract

An application maps structured UI selections to builder calls, builds a string,
stores it in its own YAML/XML/database, and later passes the loaded string to the
client. Construction needs no database connection. Execution needs no AST.

```text
UI selections -> application policy -> immutable builder -> query string
                                                        -> application storage
application storage -> query string -> HTTP client -> VictoriaMetrics
```

The application chooses allowed metrics, labels, operations and resource limits.
Repeated matcher calls are conjunctive: adding a new condition cannot overwrite
an earlier tenant or other restriction. A changed UI selection should derive a
new expression from the appropriate saved base.
MetriCraft validates its supported expression structure and keeps literal data
separate from syntax. Label values and string arguments are escaped as query
literals. Metric/label names and durations are validated; function/operator names
come from the supported catalog. A regex value intentionally remains a regex;
escaping protects query syntax, not regex semantics or computational cost.

The build guarantee applies to structured construction. MetriCraft does not parse,
sanitize or repair arbitrary query strings passed to the client, and does not own
persistence, tenant authorization, business filters or query cost policy. It does
not provide a raw-expression escape hatch in the new builder.

The client retains synchronous/asynchronous instant and range queries, metadata,
ingestion, custom transports, result models and cluster routing. Save text after
selecting the intended build mode; client-side execution does not select a dialect
or revalidate the saved query.

See the [structured selection example](examples/01_configurable_query/README.md)
and [saved query example](examples/02_saved_query/README.md).
