export interface Plan {
  metric: string;
  matchers: { label: string; op: "=" | "!="; value: string }[];
  rollup:
    | "none"
    | "rate"
    | "increase"
    | "avg_over_time"
    | "min_over_time"
    | "max_over_time"
    | "sum_over_time";
  window: number;
  aggregate: "none" | "sum" | "avg" | "min" | "max" | "count";
  grouping: "none" | "by" | "without";
  labels: string[];
  comparison: "none" | ">" | ">=" | "<" | "<=" | "==" | "!=";
  threshold: number;
}
export interface Series {
  metric: string;
  labels: Record<string, string>;
  samples: [number, number][];
}
export interface Sample {
  labels: Record<string, string>;
  value: number;
}
export const initialPlan: Plan = {
  metric: "http_requests_total",
  matchers: [{ label: "environment", op: "=", value: "production" }],
  rollup: "rate",
  window: 300,
  aggregate: "sum",
  grouping: "by",
  labels: ["service"],
  comparison: "none",
  threshold: 1,
};
export function fixture(kind: "counter" | "gauge" = "counter"): Series[] {
  return [
    ["api", "api-1", "production", 3],
    ["api", "api-2", "production", 2],
    ["worker", "worker-1", "production", 1],
    ["api", "api-staging", "staging", 4],
  ].map(([service, instance, environment, factor]) => ({
    metric: kind === "counter" ? "http_requests_total" : "queue_depth",
    labels: {
      service: String(service),
      instance: String(instance),
      environment: String(environment),
    },
    samples: Array.from({ length: 21 }, (_, i): [number, number] => [
      i * 30,
      kind === "counter"
        ? (instance === "api-2" && i >= 12 ? i - 12 : i) * 30 * Number(factor)
        : Math.round(
            20 + Number(factor) * 8 + Math.sin(i / 2 + Number(factor)) * 14,
          ),
    ]),
  }));
}

export function parseDataset(text: string): Series[] {
  if (new TextEncoder().encode(text).length > 131072)
    throw new Error("Keep sample data below 128 KiB.");
  const data: unknown = JSON.parse(text);
  if (!Array.isArray(data) || data.length > 64 || data.length === 0)
    throw new Error("Provide 1–64 series in a JSON array.");
  const keys = new Set<string>();
  return data.map((item, index) => {
    const fail = (message: string): never => {
      throw new Error(`Series ${index + 1}: ${message}`);
    };
    if (!item || typeof item !== "object" || Array.isArray(item))
      return fail("expected an object.");
    if (
      typeof item.metric !== "string" ||
      !/^[a-zA-Z_:][a-zA-Z0-9_:]*$/.test(item.metric)
    )
      return fail("metric must be a conventional Prometheus metric name.");
    if (
      !item.labels ||
      typeof item.labels !== "object" ||
      Array.isArray(item.labels)
    )
      return fail("labels must be an object.");
    const entries = Object.entries(item.labels);
    if (
      entries.length > 12 ||
      entries.some(
        ([key, value]) =>
          !/^[a-zA-Z_][a-zA-Z0-9_]*$/.test(key) ||
          key === "__name__" ||
          typeof value !== "string" ||
          value.length > 256,
      )
    )
      return fail(
        "use at most 12 string labels, without __name__; each value is at most 256 characters.",
      );
    // Empty label values and absent labels have the same identity in Prometheus.
    const labels = Object.fromEntries(
      entries.filter(([, value]) => value !== ""),
    ) as Record<string, string>;
    const identity = JSON.stringify([
      item.metric,
      Object.entries(labels).sort(([a], [b]) => a.localeCompare(b)),
    ]);
    if (keys.has(identity))
      return fail(
        "duplicate metric and labels (empty labels count as absent).",
      );
    keys.add(identity);
    if (
      !Array.isArray(item.samples) ||
      item.samples.length > 241 ||
      item.samples.length === 0
    )
      return fail("provide 1–241 [seconds, value] samples.");
    let previous = -1;
    const samples: [number, number][] = item.samples.map((pair: unknown) => {
      if (
        !Array.isArray(pair) ||
        pair.length !== 2 ||
        !pair.every((v) => typeof v === "number" && Number.isFinite(v))
      )
        return fail("samples must be pairs of finite numbers.");
      const [time, value] = pair as [number, number];
      if (Math.abs(value) > 1e12)
        return fail(
          "sample values must be within -1e12 to 1e12 for this simulator.",
        );
      if (Math.round(time * 1000) / 1000 !== time)
        return fail("timestamps support at most millisecond precision.");
      if (time < 0 || time > 3600 || time <= previous)
        return fail("timestamps must increase strictly within 0–3600 seconds.");
      previous = time;
      return [time, value];
    });
    return { metric: item.metric, labels, samples };
  });
}
