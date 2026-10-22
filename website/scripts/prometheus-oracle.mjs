/** Compare identities exactly and finite values with a small relative/absolute tolerance.
 * promtool's fuzzy_compare masks only one mantissa bit, which cannot accommodate
 * harmless changes in Prometheus aggregation order across processes.
 */
export const numericTolerance = value => Math.max(1, Math.abs(value)) * 1e-12;

function labelsText(labels) {
  return `{${Object.entries(labels).map(([key, value]) => `${key}=${JSON.stringify(value)}`).join(",")}}`;
}

function expectedVector(samples, value) {
  return samples.map(sample => {
    let expression = `vector(${value(sample.value)})`;
    for (const [label, text] of Object.entries(sample.labels)) {
      if (label === "__name__") continue; // Binary arithmetic drops the metric name.
      const replacement = JSON.stringify(text.replaceAll("$", () => "$$"));
      expression = `label_replace(${expression}, ${JSON.stringify(label)}, ${replacement}, "", "")`;
    }
    return expression;
  }).join(" or ");
}

export function assertions(expr, time, expected, data) {
  const eval_time = `${time}s`;
  if (!expected.length) return [{expr, eval_time, exp_samples: []}];
  const labels = [...new Set(["__name__", ...data.flatMap(series => Object.keys(series.labels)), ...expected.flatMap(sample => Object.keys(sample.labels))])].sort();
  return [
    {
      // Preserve the metric name too; the numeric comparison below cannot.
      expr: `group by (${labels.join(", ")}) (${expr})`, eval_time,
      exp_samples: expected.map(sample => ({labels: labelsText(sample.labels), value: 1})),
    },
    {
      // A bool comparison yields 0 for NaN/infinite or out-of-tolerance results.
      expr: `abs((${expr}) - (${expectedVector(expected, value => value)})) <= bool (${expectedVector(expected, numericTolerance)})`,
      eval_time,
      exp_samples: expected.map(sample => ({labels: labelsText(Object.fromEntries(Object.entries(sample.labels).filter(([key]) => key !== "__name__"))), value: 1})),
    },
  ];
}
