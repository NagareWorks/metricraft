# Structured language extensions

Install the published package in your application's virtual environment:

```sh
python -m pip install metricraft
```

Save [the complete example](main.py) as `main.py`, then run `python main.py`.
If you already have the repository, run
`python docs/examples/03_language_extensions/main.py` from its root.
Matching wheels include the native library; no Rust build or server is needed.
See [installation](../../getting-started.md) for supported platforms and uv usage.

The example shows shared filters, MetricsQL selector
alternatives, interval windows, aggregation limits, scoped functions and string
bindings, followed by a Prometheus duration expression.

`reference()` creates a typed symbol; it becomes valid inside its `.with_()` scope.
All binding values are expressions or escaped literals. The example prints query
strings that an application can save in its own configuration or database.

See [language support](../../language-support.md) for version and feature flags.
