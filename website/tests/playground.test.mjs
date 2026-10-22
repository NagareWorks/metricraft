import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import init, {build_query} from "../public/playground-wasm/builder.js";
import {fixture, initialPlan, parseDataset} from "../src/playground/model.ts";
import {evaluate} from "../src/playground/evaluate.ts";
import {pythonCode} from "../src/playground/python.ts";
import {cases} from "./cases.mjs";
await init({module_or_path: readFileSync(new URL("../public/playground-wasm/builder_bg.wasm", import.meta.url))});

test("real Rust builder accepts every UI path", () => {
  for (const {plan} of cases()) assert.equal(typeof build_query(JSON.stringify(plan)), "string");
});
test("hostile labels remain string literals in Rust and Python output", () => {
  const value = 'api"} or up #\n\\';
  const plan = {...initialPlan, matchers: [{label: "service", op: "=", value}]};
  assert.ok(build_query(JSON.stringify(plan)).includes('service="api\\"} or up #\\n\\\\"'));
  assert.ok(pythonCode(plan).includes(JSON.stringify(value)));
});
test("Rust boundary rejects unsupported plans and excess configuration", () => {
  for (const patch of [{rollup: "unknown"}, {window: 0}, {window: 3601}, {aggregate: "unknown"},
    {grouping: "both"}, {labels: ["job", "job"]}, {comparison: "or"},
    {matchers: [{label: "job", op: "=~", value: ".*"}]}, {extra: true}, {metric: "x".repeat(17000)}])
    assert.throws(() => build_query(JSON.stringify({...initialPlan, ...patch})));
});
test("counter reset is handled before aggregation", () => {
  const result = evaluate(initialPlan, fixture(), 600);
  assert.deepEqual(result.map(s => [s.labels.service, s.value]), [["api", 4.777777777777778], ["worker", 1]]);
});
test("range and instant lookback exclude the left boundary", () => {
  const data = [{metric: "m", labels: {}, samples: [[0, 20], [300, 40]]}];
  const p = {...initialPlan, metric: "m", matchers: [], aggregate: "none", grouping: "none", labels: [], rollup: "avg_over_time"};
  assert.equal(evaluate(p, data, 300)[0].value, 40);
  assert.deepEqual(evaluate(p, data, 600), []);
  assert.equal(evaluate({...p, rollup: "none"}, data, 599)[0].value, 40);
  assert.deepEqual(evaluate({...p, rollup: "none"}, data, 600), []);
  assert.deepEqual(evaluate({...p, rollup: "none"}, data, 601), []);
});
test("filters handle absent labels and empty aggregate results", () => {
  assert.equal(evaluate({...initialPlan, matchers: [{label: "missing", op: "=", value: ""}]}, fixture(), 600).length, 2);
  assert.deepEqual(evaluate({...initialPlan, matchers: [{label: "missing", op: "!=", value: ""}]}, fixture(), 600), []);
});
test("dataset edits reject ambiguous identity and invalid samples", () => {
  const one = {metric: "m", labels: {}, samples: [[0, 0], [30, 1]]};
  assert.equal(parseDataset(JSON.stringify([one])).length, 1);
  for (const value of [[], [one, {...one, labels: {empty: ""}}], [{...one, samples: [[30, 1], [0, 0]]}],
    [{...one, samples: [[0, null]]}], [{...one, labels: {__name__: "other"}}], Array(65).fill(one)])
    assert.throws(() => parseDataset(JSON.stringify(value)));
});
