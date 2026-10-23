# Save query text and execute it later

This application builds a query string, writes and reads it using SQLite, then
passes the loaded string to the client. The SQLite code belongs to the example
application; the SDK has no persistence API. YAML, XML or another database can
serve the same role.

Install the published package in your application's virtual environment:

```sh
python -m pip install metricraft
```

Save [the complete example](main.py) as `main.py`, then run `python main.py`.
Matching wheels include the native library; no Rust build is needed.
If you already have the repository, you can instead run
`python docs/examples/02_saved_query/main.py` from its root.
See [installation](../../getting-started.md) for supported platforms and uv usage.

The default uses an in-memory database and an injected offline HTTP transport.
To keep the application's database and query a real single-node VictoriaMetrics:

```sh
python main.py --database queries.sqlite --url http://localhost:8428
```

The endpoint is supplied by the application. No deployment or dashboard is included.
`DatabaseClient` accepts the loaded string directly, without parsing, escaping or
sanitizing it. The safe-construction boundary ended when `build()` returned text;
the application owns subsequent edits, storage integrity and access control.

For client-only use, construct `DatabaseClient(VMSingleConfig(url))` and call
`client.query(loaded_text)` without importing a builder or loading a native library.
