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
  const withoutName = samples => samples.map(sample => ({labels: labelsText(Object.fromEntries(Object.entries(sample.labels).filter(([key]) => key !== "__name__"))), value: 1}));
  const finite = expected.filter(sample => Number.isFinite(sample.value));
  const checks = [{
      // Preserve the metric name too; the numeric comparison below cannot.
      expr: `group by (${labels.join(", ")}) (${expr})`, eval_time,
      exp_samples: expected.map(sample => ({labels: labelsText(sample.labels), value: 1})),
    }];
  if (finite.length) checks.push({
      // A bool comparison yields 0 for NaN/infinite or out-of-tolerance results.
      expr: `abs((${expr}) - (${expectedVector(finite, value => value)})) <= bool (${expectedVector(finite, numericTolerance)})`,
      eval_time,
      exp_samples: withoutName(finite),
  });
  for (const [value, check] of [[NaN, `(${expr}) != bool (${expr})`], [Infinity, `(${expr}) == bool +Inf`], [-Infinity, `(${expr}) == bool -Inf`]]) {
    const samples = expected.filter(sample => Object.is(sample.value, value));
    if (samples.length) checks.push({
      expr: `(${check}) and (${expectedVector(samples, () => 1)})`, eval_time,
      exp_samples: withoutName(samples),
    });
  }
  return checks;
}
