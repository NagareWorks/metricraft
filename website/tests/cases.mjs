import {fixture, initialPlan} from "../src/playground/model.ts";
export function cases() {
  const result = [];
  for (const rollup of ["none", "rate", "increase", "avg_over_time", "min_over_time", "max_over_time", "sum_over_time"])
    for (const aggregate of ["none", "sum", "avg", "min", "max", "count"])
      for (const grouping of aggregate === "none" ? ["none"] : ["none", "by", "without"]) {
        result.push({plan: {...initialPlan, rollup, aggregate, grouping, labels: grouping === "none" ? [] : [grouping === "by" ? "service" : "instance"]}, data: fixture()});
      }
  for (const comparison of [">", ">=", "<", "<=", "==", "!="])
    result.push({plan: {...initialPlan, comparison, threshold: 5}, data: fixture()});
  for (const op of ["=", "!="])
    for (const value of ["", "production", 'api"} or up #'])
      result.push({plan: {...initialPlan, matchers: [{label: "environment", op, value}]}, data: fixture()});
  const regexData = ["api", "api-1", "worker", "", "API", "api\n1", "api.prod", "中文", "１２", "123", 'a"b\\c'].map((job, i) => ({
    metric: initialPlan.metric, labels: {...(job ? {job} : {}), id: String(i)}, samples: [[0, i], [300, i + 1], [600, i + 2]],
  }));
  regexData.push({metric: initialPlan.metric, labels: {id: "missing"}, samples: [[0, 7], [300, 8], [600, 9]]});
  for (const op of ["=~", "!~"])
    for (const value of ["api", "api.*", "api|worker", "", ".*", ".+", "(?i)api", "(?-s)api.*", "(?m)^api$", "\\d+", "\\w+", "[[:alpha:]]+", "\\p{Han}+", "\\Qapi.prod\\E", 'a"b\\\\c'])
      result.push({plan: {...initialPlan, rollup: "none", aggregate: "none", grouping: "none", labels: [], matchers: [{label: "job", op, value}]}, data: regexData});
  for (const arithmetic of ["+", "-", "*", "/", "%", "**", "negate", "positive"])
    for (const scalarSide of ["+", "-", "*", "/"].includes(arithmetic) ? ["left", "right"] : ["right"])
      for (const operand of [-2, 0, 2])
        result.push({plan: {...initialPlan, rollup: "none", aggregate: "none", grouping: "none", labels: [], matchers: [], arithmetic, operand, scalarSide}, data: [
          {metric: initialPlan.metric, labels: {job: "api"}, samples: [[0, -5], [300, 0], [600, 5]]},
        ]});
  result.push({plan: {...initialPlan, metric: "queue_depth", rollup: "avg_over_time"}, data: fixture("gauge")});
  result.push({plan: {...initialPlan, aggregate: "none", grouping: "none", labels: [], matchers: []}, data: [
    {metric: initialPlan.metric, labels: {}, samples: [[0, 7], [90, 12], [120, 2], [270, 10], [300, 10], [600, 30]]},
  ]});
  result.push({plan: {...initialPlan, rollup: "none", aggregate: "none", grouping: "none", labels: [], matchers: [{label: "absent", op: "=", value: ""}]}, data: fixture()});
  return result;
}
