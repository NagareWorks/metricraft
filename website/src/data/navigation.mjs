export const repository = "https://github.com/NagareWorks/metricraft";
export const groups = [
  {
    title: "Start here",
    pages: [
      {
        slug: "getting-started",
        source: "docs/getting-started.md",
        title: "Your first query",
        description:
          "Install the SDK, compose a query, and choose how to execute it.",
      },
      {
        slug: "concepts",
        source: "docs/concepts.md",
        title: "A few useful ideas",
        description:
          "Immutable expressions, two dialects, and a clear boundary between building and execution.",
      },
    ],
  },
  {
    title: "Work with the SDK",
    pages: [
      {
        slug: "guides/building-queries",
        source: "docs/building-queries.md",
        title: "Build queries",
        description:
          "Compose selectors, rollups, aggregates and matching rules from structured inputs.",
      },
      {
        slug: "guides/client",
        source: "docs/client-guide.md",
        title: "Query your backend",
        description:
          "Use the synchronous or asynchronous client with Prometheus and VictoriaMetrics.",
      },
      {
        slug: "guides/configurable-queries",
        source: "docs/configurable-query-contract.md",
        title: "Accept application inputs",
        description:
          "Map application choices to allowed operations and keep query values as data.",
      },
      {
        slug: "guides/language-support",
        source: "docs/language-support.md",
        title: "Language support",
        description:
          "Supported PromQL and MetricsQL forms, version baselines and explicit feature flags.",
      },
    ],
  },
  {
    title: "Examples",
    pages: [
      {
        slug: "examples/structured-selections",
        source: "docs/examples/01_configurable_query/README.md",
        title: "From UI selections",
        description:
          "Turn a validated set of application selections into a reusable query string.",
      },
      {
        slug: "examples/saved-queries",
        source: "docs/examples/02_saved_query/README.md",
        title: "Save now, query later",
        description:
          "Store query text with your application, then execute it through the client.",
      },
      {
        slug: "examples/language-extensions",
        source: "docs/examples/03_language_extensions/README.md",
        title: "Use language extensions",
        description:
          "Explore explicit feature flags, label operations and scoped MetricsQL templates.",
      },
    ],
  },
  {
    title: "Reference",
    pages: [
      {
        slug: "reference/api",
        source: "docs/api-reference.md",
        title: "Python API",
        description:
          "Find public builder, client and configuration methods with signatures from the source.",
      },
      {
        slug: "reference/migration",
        source: "docs/legacy-api-migration.md",
        title: "Migrate existing code",
        description:
          "Find the current equivalent of historical APIs, including intentional removals.",
      },
    ],
  },
  {
    title: "Under the hood",
    pages: [
      {
        slug: "internals/architecture",
        source: "docs/architecture.md",
        title: "Architecture",
        description:
          "A shared Rust expression tree, a small C ABI and an independent Python HTTP client.",
      },
      {
        slug: "internals/memory",
        source: "docs/memory.md",
        title: "Sharing and memory",
        description:
          "Understand shared ownership, build budgets, retained roots and measured memory behavior.",
      },
      {
        slug: "internals/benchmarks",
        source: "benchmarks/README.md",
        title: "Performance measurements",
        description:
          "Reproduce construction, rendering, FFI and memory measurements with the unified suite.",
      },
      {
        slug: "internals/backend-validation",
        source: "docs/backend-validation.md",
        title: "Backend verification",
        description:
          "Verify generated queries against real backends and explicit expected results.",
      },
      {
        slug: "internals/rust-migration",
        source: "docs/rust-migration.md",
        title: "Rust migration status",
        description:
          "The current native architecture, validation evidence and release boundary.",
      },
      {
        slug: "internals/comparison",
        source: "docs/api-comparison.md",
        title: "Compared with Grafana",
        description:
          "Compare construction styles, client capabilities and responsibility boundaries.",
      },
      {
        slug: "contributing",
        source: "CONTRIBUTING.md",
        title: "Contribute",
        description:
          "Set up a checkout, validate a change and understand the contribution workflow.",
      },
    ],
  },
];
export const pages = groups.flatMap((group) =>
  group.pages.map((page) => ({ ...page, group: group.title })),
);
export function href(slug = "") {
  return `${import.meta.env.BASE_URL.replace(/\/$/, "")}/${slug ? `${slug}/` : ""}`;
}
