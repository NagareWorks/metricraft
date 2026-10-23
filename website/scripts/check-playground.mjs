/** Differential checks: the copied Python must match WASM; promtool checks the simulator. */
import {readFileSync, writeFileSync, mkdirSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {resolve, delimiter} from "node:path";
import init, {build_query} from "../public/playground-wasm/builder.js";
import {evaluate} from "../src/playground/evaluate.ts";
import {pythonCode} from "../src/playground/python.ts";
import {cases} from "../tests/cases.mjs";
import {assertions} from "./prometheus-oracle.mjs";
await init({module_or_path: readFileSync(new URL("../public/playground-wasm/builder_bg.wasm", import.meta.url))});
const all = cases();
const special = {...all[0].plan, matchers: [{label: "job", op: "=", value: 'x"} or up #\n\\\t中文'}]};
const plans = [...all.map(c => c.plan), special];
const snippets = plans.map(pythonCode);
const python = spawnSync(process.env.PYTHON || "python", ["-X", "utf8", "-c", `
import contextlib, io, json, sys
result = []
for snippet in json.load(sys.stdin):
    scope = {}
    with contextlib.redirect_stdout(io.StringIO()):
        exec(snippet, scope)
    result.append(scope['query'])
json.dump(result, sys.stdout)
`], {input: JSON.stringify(snippets), encoding: "utf8", env: {...process.env, PYTHONPATH: [resolve("../python/metricraft/src"), process.env.PYTHONPATH || ""].join(delimiter)}});
if (python.status !== 0) throw new Error(python.stderr || String(python.error));
const actual = JSON.parse(python.stdout);
plans.forEach((plan, i) => {if (actual[i] !== build_query(JSON.stringify(plan))) throw new Error(`Python/WASM mismatch in example ${i}`);});
console.log(`Python/WASM parity: ${plans.length} copied snippets agree.`);
const tests = all.flatMap(({plan, data}) => {
  const input_series = data.map(s => {
    const labelText = Object.entries(s.labels).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(",");
    const values = new Map(s.samples);
    return {series: `${s.metric}{${labelText}}`, values: Array.from({length: 21}, (_, i) => values.has(i * 30) ? String(values.get(i * 30)) : "_").join(" ")};
  });
  return [0, 30, 300, 600, 900, 901].map(time => ({interval: "30s", input_series,
    promql_expr_test: assertions(build_query(JSON.stringify(plan)), time, evaluate(plan, data, time), data),
  }));
});
const output = resolve(".generated/playground-prometheus.json");
mkdirSync(resolve(".generated"), {recursive: true});
writeFileSync(output, JSON.stringify({evaluation_interval: "1s", tests}));
const promtool = spawnSync(process.env.PROMTOOL || "promtool", ["test", "rules", output], {encoding: "utf8"});
if (promtool.status !== 0) throw new Error(promtool.stdout + promtool.stderr || String(promtool.error));
console.log(`Prometheus differential evaluation: ${tests.length} scenarios passed.`);

// Exercise the comparison itself, including deliberately wrong expected results.
const baseline = {labels: {__name__: "m", job: "$literal"}, value: 0.2};
const controls = [
  ["exact", [baseline], true],
  ["roundoff", [{...baseline, value: 0.19999999999999998}], true],
  ["wrong value", [{...baseline, value: 0.21}], false],
  ["wrong label", [{...baseline, labels: {...baseline.labels, job: "other"}}], false],
  ["wrong metric name", [{...baseline, labels: {...baseline.labels, __name__: "other"}}], false],
  ["missing series", [], false],
  ["non-finite NaN", [baseline], false, "NaN"],
  ["non-finite infinity", [baseline], false, "+Inf"],
  ["expected NaN", [{...baseline, value: NaN}], true, "NaN"],
  ["expected infinity", [{...baseline, value: Infinity}], true, "+Inf"],
  ["expected negative infinity", [{...baseline, value: -Infinity}], true, "-Inf"],
  ["wrong infinity sign", [{...baseline, value: Infinity}], false, "-Inf"],
  ["finite instead of NaN", [{...baseline, value: NaN}], false],
];
for (const [name, expected, shouldPass, inputValue = "0.2"] of controls) {
  const controlPath = resolve(".generated/oracle-control.json");
  writeFileSync(controlPath, JSON.stringify({evaluation_interval: "1s", tests: [{
    interval: "1s", input_series: [{series: 'm{job="$literal"}', values: inputValue}],
    promql_expr_test: assertions("m", 0, expected, [{labels: {job: "$literal"}}]),
  }]}));
  const run = spawnSync(process.env.PROMTOOL || "promtool", ["test", "rules", controlPath], {encoding: "utf8"});
  const report = (run.stdout || "") + (run.stderr || "");
  if (shouldPass ? run.status !== 0 : run.status !== 1 || !report.includes("exp:") || !report.includes("got:"))
    throw new Error(`Oracle control '${name}' did not ${shouldPass ? "accept" : "reject"} the result: ${report || run.error}`);
}
console.log(`Oracle controls: ${controls.length} acceptance/rejection checks passed.`);
