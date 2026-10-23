import assert from "node:assert/strict";
import test from "node:test";
import {readFileSync} from "node:fs";
import init, {build_query} from "../public/playground-wasm/builder.js";
import {fixture, initialPlan, parseDataset} from "../src/playground/model.ts";
import {evaluate} from "../src/playground/evaluate.ts";
import {pythonCode} from "../src/playground/python.ts";
import {compileMatchers} from "../src/playground/matchers.ts";
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
    {matchers: [{label: "job", op: "unknown", value: ".*"}]}, {extra: true}, {metric: "x".repeat(17000)},
    {arithmetic: "unknown"}, {scalarSide: "unknown"}, {arithmetic: "%", scalarSide: "left"}, {arithmetic: "**", scalarSide: "left"}])
    assert.throws(() => build_query(JSON.stringify({...initialPlan, ...patch})));
});

test("regex filters use fully anchored RE2 semantics, including absent labels", () => {
  const matches = (op, value, labels) => compileMatchers([{label: "job", op, value}])(labels);
  assert.equal(matches("=~", "api", {job: "api-1"}), false);
  assert.equal(matches("=~", "api.*", {job: "api\n1"}), true);
  assert.equal(matches("!~", "api.*", {job: "api-1"}), false);
  assert.equal(matches("=~", ".*", {}), true);
  assert.equal(matches("!~", ".+", {}), true);
  assert.equal(matches("=~", "\\d+", {job: "１２"}), false);
  assert.equal(matches("=~", "(?i)api|worker", {job: "API"}), true);
  assert.equal(matches("=~", "\\Qapi.prod\\E", {job: "api.prod"}), true);
  for (const value of ["[", "(?=api)", "(?<=api).*", "(api)\\1", "a{1001}"])
    assert.throws(() => compileMatchers([{label: "job", op: "=~", value}]), /Invalid regex/);
});

test("Python output demonstrates regex, arithmetic and comparison overloads", () => {
  const plan = {...initialPlan, matchers: [{label: "instance", op: "=~", value: "api-.*"}, {label: "environment", op: "!~", value: "staging"}], arithmetic: "*", operand: 100, comparison: ">", threshold: 5};
  const source = pythonCode(plan);
  assert.ok(source.includes('.where_regex("instance", "api-.*")'));
  assert.ok(source.includes('.where_not_regex("environment", "staging")'));
  assert.ok(source.includes("expression = expression * 100"));
  assert.ok(source.includes("expression = expression > 5"));
});
test("counter reset is handled before aggregation", () => {
  const result = evaluate(initialPlan, fixture(), 600);
  assert.deepEqual(result.map(s => [s.labels.service, s.value]), [["api", 4.777777777777778], ["worker", 1]]);
});

test("unary minus drops the metric name while unary plus preserves it", () => {
  const plan = {...initialPlan, metric: "m", matchers: [], aggregate: "none", grouping: "none", labels: [], rollup: "none"};
  const data = [{metric: "m", labels: {job: "api"}, samples: [[0, 5]]}];
  assert.deepEqual(evaluate({...plan, arithmetic: "negate"}, data, 0), [{labels: {job: "api"}, value: -5}]);
  assert.deepEqual(evaluate({...plan, arithmetic: "positive"}, data, 0), [{labels: {__name__: "m", job: "api"}, value: 5}]);
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
