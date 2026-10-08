# Structured language extensions

Run `python docs/examples/03_language_extensions/main.py` after building the native
library. No server is needed. The example shows shared filters, MetricsQL selector
alternatives, interval windows, aggregation limits, scoped functions and string
bindings, followed by a Prometheus duration expression.

`reference()` creates a typed symbol; it becomes valid inside its `.with_()` scope.
All binding values are expressions or escaped literals. The example prints query
strings that an application can save in its own configuration or database.

See [language support](../../language-support.md) for version and feature flags.
