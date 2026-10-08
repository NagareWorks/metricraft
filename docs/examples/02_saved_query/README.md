# Save query text and execute it later

This application builds a query string, writes and reads it using SQLite, then
passes the loaded string to the client. The SQLite code belongs to the example
application; the SDK has no persistence API. YAML, XML or another database can
serve the same role.

After the [development setup](../../../CONTRIBUTING.md), run:

```sh
python docs/examples/02_saved_query/main.py
```

The default uses an in-memory database and an injected offline HTTP transport.
To keep the application's database and query a real single-node VictoriaMetrics:

```sh
python docs/examples/02_saved_query/main.py --database queries.sqlite --url http://localhost:8428
```

The endpoint is supplied by the application. No deployment or dashboard is included.
`DatabaseClient` accepts the loaded string directly, without parsing, escaping or
sanitizing it. The safe-construction boundary ended when `build()` returned text;
the application owns subsequent edits, storage integrity and access control.

For client-only use, construct `DatabaseClient(VMSingleConfig(url))` and call
`client.query(loaded_text)` without importing a builder or loading a native library.
