import type { Plan } from "./model.ts";

/** JSON string escapes are also valid Python string-literal escapes for these inputs. */
const literal = (value: string) => JSON.stringify(value);
export function pythonCode(plan: Plan): string {
  const lines = [
    "from metricraft import QueryBuilder as Q",
    "",
    "expression = (",
    `    Q.from_metric(${literal(plan.metric)})`,
  ];
  const matcherMethods = {
    "=": "where_eq",
    "!=": "where_ne",
    "=~": "where_regex",
    "!~": "where_not_regex",
  };
  for (const filter of plan.matchers)
    lines.push(
      `    .${matcherMethods[filter.op]}(${literal(filter.label)}, ${literal(filter.value)})`,
    );
  if (plan.rollup !== "none")
    lines.push(`    .${plan.rollup}(${literal(`${plan.window}s`)})`);
  if (plan.aggregate !== "none") {
    lines.push(`    .${plan.aggregate}()`);
    if (plan.grouping !== "none")
      lines.push(
        `    .${plan.grouping}(${plan.labels.map(literal).join(", ")})`,
      );
  }
  lines.push(")");
  if (plan.arithmetic === "negate" || plan.arithmetic === "positive") {
    lines.push(
      `expression = ${plan.arithmetic === "negate" ? "-" : "+"}expression`,
    );
  } else if (plan.arithmetic !== "none") {
    const scalar =
      plan.operand < 0 ? `(${plan.operand})` : String(plan.operand);
    const operands =
      plan.scalarSide === "left"
        ? [scalar, "expression"]
        : ["expression", scalar];
    lines.push(`expression = ${operands[0]} ${plan.arithmetic} ${operands[1]}`);
  }
  if (plan.comparison !== "none")
    lines.push(`expression = expression ${plan.comparison} ${plan.threshold}`);
  lines.push('query = expression.build(mode="promql")', "print(query)");
  return lines.join("\n");
}
