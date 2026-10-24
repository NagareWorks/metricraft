import apiCategories from "./api-categories.json";
import chinese from "./navigation.zh.json";
import { localizedPath, localizedSource } from "./locales.mjs";
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
        slug: "playground",
        source: "docs/playground.md",
        title: "Query playground",
        description:
          "Choose monitoring filters, see live Python and PromQL, and query editable sample data.",
      },
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
      ...apiCategories.map((category) => ({
        slug: `reference/api/${category.id}`,
        source: `docs/reference/${category.id}.md`,
        title: category.title,
        description: category.description,
        apiCategory: category.id,
        parent: "reference/api",
      })),
      {
        slug: "reference/models",
        source: "docs/models.md",
        title: "Models & shared types",
        parent: "reference/api",
        description:
          "Result fields, ingestion data, time values, registry helpers and errors.",
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
export function localizedPage(page, locale = "en") {
  if (locale === "en") return page;
  const translation = chinese.pages[page.slug];
  if (!translation) throw new Error(`Missing Chinese navigation: ${page.slug}`);
  return {
    ...page,
    title: translation[0],
    description: translation[1],
    source: localizedSource(page.source, locale),
    group: chinese.groups[page.group] || page.group,
  };
}
export function localizedGroups(locale = "en") {
  return groups.map((group) => ({
    title: locale === "zh" ? chinese.groups[group.title] : group.title,
    pages: group.pages.map((page) => localizedPage(page, locale)),
  }));
}
export function href(slug = "", locale = "en") {
  return localizedPath(import.meta.env.BASE_URL, slug, locale);
}
export function asset(path = "") {
  return `${import.meta.env.BASE_URL.replace(/\/$/, "")}/${path}`;
}
