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
  for (const filter of plan.matchers)
    lines.push(
      `    .${filter.op === "=" ? "where_eq" : "where_ne"}(${literal(filter.label)}, ${literal(filter.value)})`,
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
  if (plan.comparison !== "none") {
    const methods = {
      ">": "gt",
      ">=": "ge",
      "<": "lt",
      "<=": "le",
      "==": "eq",
      "!=": "ne",
    };
    lines.push(`    .${methods[plan.comparison]}(${plan.threshold})`);
  }
  lines.push(")", 'query = expression.build(mode="promql")', "print(query)");
  return lines.join("\n");
}
