/** Demo-only evaluation of the structured UI plan. No parsing or execution of query text.
 * Finite input samples only: no stale markers, histograms or binary vector joins.
 * Prometheus rate extrapolation follows the pinned backend's float algorithm.
 */
import type { Plan, Sample, Series } from "./model.ts";
import { compileMatchers, type LabelPredicate } from "./matchers.ts";

function counter(
  samples: [number, number][],
  start: number,
  end: number,
  rate: boolean,
): number | undefined {
  if (samples.length < 2) return undefined;
  const first = samples[0],
    last = samples[samples.length - 1];
  let delta = last[1] - first[1];
  for (let i = 1; i < samples.length; i++)
    if (samples[i][1] < samples[i - 1][1]) delta += samples[i - 1][1];
  const interval = last[0] - first[0];
  const average = interval / (samples.length - 1);
  let toStart = first[0] - start;
  let toEnd = end - last[0];
  if (toStart >= average * 1.1) toStart = average / 2;
  if (delta > 0 && first[1] >= 0)
    toStart = Math.min(toStart, (interval * first[1]) / delta);
  if (toEnd >= average * 1.1) toEnd = average / 2;
  const result = (delta * (interval + toStart + toEnd)) / interval;
  return rate ? result / (end - start) : result;
}

export function evaluate(
  plan: Plan,
  data: Series[],
  time: number,
  matches: LabelPredicate = compileMatchers(plan.matchers),
): Sample[] {
  const vector: Sample[] = [];
  for (const series of data) {
    const labels = { ...series.labels, __name__: series.metric };
    if (series.metric !== plan.metric || !matches(labels)) continue;
    let value: number | undefined;
    if (plan.rollup === "none") {
      // Prometheus 3.15 excludes the exact lookback boundary.
      value = series.samples
        .filter(([t]) => t <= time && t > time - 300)
        .at(-1)?.[1];
    } else {
      // Range selectors exclude the left boundary and include the right boundary.
      const samples = series.samples.filter(
        ([t]) => t > time - plan.window && t <= time,
      );
      const values = samples.map(([, v]) => v);
      if (plan.rollup === "rate" || plan.rollup === "increase") {
        value = counter(
          samples,
          time - plan.window,
          time,
          plan.rollup === "rate",
        );
      } else if (values.length) {
        if (plan.rollup === "min_over_time") value = Math.min(...values);
        if (plan.rollup === "max_over_time") value = Math.max(...values);
        if (
          plan.rollup === "sum_over_time" ||
          plan.rollup === "avg_over_time"
        ) {
          value = values.reduce((a, b) => a + b, 0);
          if (plan.rollup === "avg_over_time") value /= values.length;
        }
      }
      delete (labels as Record<string, string>).__name__;
    }
    if (value !== undefined) vector.push({ labels, value });
  }
  let result = vector;
  if (plan.aggregate !== "none") {
    const groups = new Map<
      string,
      { labels: Record<string, string>; values: number[] }
    >();
    for (const sample of vector) {
      const labels = Object.fromEntries(
        Object.entries(sample.labels)
          .filter(([label]) =>
            plan.grouping === "by"
              ? plan.labels.includes(label)
              : plan.grouping === "without" &&
                label !== "__name__" &&
                !plan.labels.includes(label),
          )
          .sort(([a], [b]) => a.localeCompare(b)),
      );
      const key = JSON.stringify(labels);
      if (!groups.has(key)) groups.set(key, { labels, values: [] });
      groups.get(key)!.values.push(sample.value);
    }
    result = [...groups.values()].map(({ labels, values }) => {
      let value = values.reduce((a, b) => a + b, 0);
      if (plan.aggregate === "avg") value /= values.length;
      if (plan.aggregate === "min") value = Math.min(...values);
      if (plan.aggregate === "max") value = Math.max(...values);
      if (plan.aggregate === "count") value = values.length;
      return { labels, value };
    });
  }
  if (plan.arithmetic !== "none") {
    result = result.map(({ labels, value }) => {
      if (plan.arithmetic === "positive") return { labels, value };
      const outputLabels = { ...labels };
      delete outputLabels.__name__;
      if (plan.arithmetic === "negate")
        return { labels: outputLabels, value: -value };
      const [left, right] =
        plan.scalarSide === "left"
          ? [plan.operand, value]
          : [value, plan.operand];
      switch (plan.arithmetic) {
        case "+":
          value = left + right;
          break;
        case "-":
          value = left - right;
          break;
        case "*":
          value = left * right;
          break;
        case "/":
          value = left / right;
          break;
        case "%":
          value = left % right;
          break;
        case "**":
          value = left ** right;
          break;
      }
      return { labels: outputLabels, value };
    });
  }
  return result.filter(({ value }) => {
    switch (plan.comparison) {
      case ">":
        return value > plan.threshold;
      case ">=":
        return value >= plan.threshold;
      case "<":
        return value < plan.threshold;
      case "<=":
        return value <= plan.threshold;
      case "==":
        return value === plan.threshold;
      case "!=":
        return value !== plan.threshold;
      default:
        return true;
    }
  });
}
