/** Differential checks: the copied Python must match WASM; promtool checks the simulator. */
import {readFileSync, writeFileSync, mkdirSync} from "node:fs";
import {spawnSync} from "node:child_process";
import {resolve, delimiter} from "node:path";
import init, {build_query} from "../public/playground-wasm/builder.js";
import {evaluate} from "../src/playground/evaluate.ts";
import {pythonCode} from "../src/playground/python.ts";
import {cases} from "../tests/cases.mjs";
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
    promql_expr_test: [{expr: build_query(JSON.stringify(plan)), eval_time: `${time}s`, exp_samples: evaluate(plan, data, time).map(s => ({
      labels: `{${Object.entries(s.labels).map(([k,v]) => `${k}=${JSON.stringify(v)}`).join(",")}}`, value: s.value,
    }))}],
  }));
});
const output = resolve(".generated/playground-prometheus.json");
mkdirSync(resolve(".generated"), {recursive: true});
writeFileSync(output, JSON.stringify({evaluation_interval: "1s", fuzzy_compare: true, tests}));
const promtool = spawnSync(process.env.PROMTOOL || "promtool", ["test", "rules", output], {encoding: "utf8"});
if (promtool.status !== 0) throw new Error(promtool.stdout + promtool.stderr || String(promtool.error));
console.log(`Prometheus differential evaluation: ${tests.length} scenarios passed.`);
