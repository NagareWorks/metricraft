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
  result.push({plan: {...initialPlan, metric: "queue_depth", rollup: "avg_over_time"}, data: fixture("gauge")});
  result.push({plan: {...initialPlan, aggregate: "none", grouping: "none", labels: [], matchers: []}, data: [
    {metric: initialPlan.metric, labels: {}, samples: [[0, 7], [90, 12], [120, 2], [270, 10], [300, 10], [600, 30]]},
  ]});
  result.push({plan: {...initialPlan, rollup: "none", aggregate: "none", grouping: "none", labels: [], matchers: [{label: "absent", op: "=", value: ""}]}, data: fixture()});
  return result;
}
