import {
  fixture,
  initialPlan,
  parseDataset,
  type Plan,
  type Series,
} from "./model.ts";
import { evaluate } from "./evaluate.ts";
import { pythonCode } from "./python.ts";
import { compileMatchers, type LabelPredicate } from "./matchers.ts";
import { translator } from "../data/translate";
const locale = document.documentElement.lang.startsWith("zh") ? "zh" : "en";
const t = translator(locale);

const el = <T extends HTMLElement>(id: string) =>
  document.getElementById(id) as T;
const form = el<HTMLFormElement>("query-controls");
const field = (name: string) =>
  el<HTMLInputElement | HTMLSelectElement>(`lab-${name}`);
const dataEditor = el<HTMLTextAreaElement>("sample-data");
const runButton = el<HTMLButtonElement>("run-query");
let build: ((input: string) => string) | undefined;
let currentPlan: Plan | undefined;
let data: Series[] | undefined;
const error = el("lab-error");
const rows = el("filter-rows");

function addFilter(label = "", op = "=", value = "") {
  if (rows.children.length >= 12) return;
  const row = document.createElement("div");
  row.className = "lab-filter-row";
  const key = document.createElement("input");
  key.value = label;
  key.placeholder = t("Label");
  key.required = true;
  key.setAttribute("aria-label", t("Filter label"));
  key.setAttribute("list", "lab-labels");
  key.maxLength = 256;
  const operator = document.createElement("select");
  operator.setAttribute("aria-label", t("Filter operator"));
  for (const text of ["=", "!=", "=~", "!~"])
    operator.add(new Option(text, text));
  operator.value = op;
  const literal = document.createElement("input");
  literal.value = value;
  literal.placeholder = t("Value");
  literal.setAttribute("aria-label", t("Filter value"));
  literal.setAttribute("list", "lab-values");
  literal.maxLength = 256;
  const describeValue = () => {
    const regex = operator.value === "=~" || operator.value === "!~";
    literal.placeholder = regex ? t("Regex, e.g. api-.*") : t("Value");
    literal.setAttribute(
      "aria-label",
      regex ? t("Filter regex pattern") : t("Filter value"),
    );
    if (regex) literal.removeAttribute("list");
    else literal.setAttribute("list", "lab-values");
  };
  operator.addEventListener("change", describeValue);
  describeValue();
  const remove = document.createElement("button");
  remove.type = "button";
  remove.textContent = "×";
  remove.setAttribute("aria-label", t("Remove filter"));
  remove.addEventListener("click", () => {
    row.remove();
    update();
    el("add-filter").focus();
  });
  row.append(key, operator, literal, remove);
  rows.append(row);
  el<HTMLButtonElement>("add-filter").disabled = rows.children.length >= 12;
}

function plan(): Plan {
  if (!form.checkValidity())
    throw new Error(
      t(
        "Complete the filters and use a whole-number window from 1 to 3600 seconds.",
      ),
    );
  const aggregate = field("aggregate").value as Plan["aggregate"];
  const grouping =
    aggregate === "none"
      ? "none"
      : (field("grouping").value as Plan["grouping"]);
  return {
    metric: field("metric").value,
    matchers: [...rows.children].map((row) => {
      const [label, value] = row.querySelectorAll("input");
      return {
        label: label.value,
        op: row.querySelector("select")!
          .value as Plan["matchers"][number]["op"],
        value: value.value,
      };
    }),
    rollup: field("rollup").value as Plan["rollup"],
    window:
      field("rollup").value === "none" ? 300 : Number(field("window").value),
    aggregate,
    grouping,
    labels:
      grouping === "none"
        ? []
        : field("group-labels")
            .value.split(",")
            .map((s) => s.trim())
            .filter(Boolean),
    comparison: field("comparison").value as Plan["comparison"],
    arithmetic: field("arithmetic").value as Plan["arithmetic"],
    // JSON serializes -0 as 0; keep the simulator and the WASM input identical.
    operand: field("operand").disabled
      ? 100
      : Number(field("operand").value) || 0,
    scalarSide: field("scalar-side").disabled
      ? "right"
      : (field("scalar-side").value as Plan["scalarSide"]),
    threshold:
      field("comparison").value === "none"
        ? 0
        : Number(field("threshold").value),
  };
}
function clearResults(
  message = t("Selections changed. Run the query to refresh results."),
) {
  el("result-status").textContent = message;
  el("result-chart").replaceChildren();
  el("result-rows").replaceChildren();
  el("result-empty").hidden = true;
}
function update() {
  clearResults();
  currentPlan = undefined;
  field("grouping").disabled = field("aggregate").value === "none";
  field("group-labels").disabled =
    field("aggregate").value === "none" || field("grouping").value === "none";
  field("window").disabled = field("rollup").value === "none";
  field("threshold").disabled = field("comparison").value === "none";
  const arithmetic = field("arithmetic").value;
  field("operand").disabled = ["none", "negate", "positive"].includes(
    arithmetic,
  );
  field("scalar-side").disabled = [
    "none",
    "negate",
    "positive",
    "%",
    "**",
  ].includes(arithmetic);
  if (field("scalar-side").disabled) field("scalar-side").value = "right";
  el<HTMLButtonElement>("add-filter").disabled = rows.children.length >= 12;
  if (!build) return;
  try {
    const next = plan();
    compileMatchers(next.matchers);
    const query = build(JSON.stringify(next));
    el("python-output").textContent = pythonCode(next);
    el("promql-output").textContent = query;
    currentPlan = next;
    error.textContent = "";
  } catch (e) {
    error.textContent = String(e);
    el("python-output").textContent = t(
      "Fix the configuration to generate Python.",
    );
    el("promql-output").textContent = t(
      "Fix the configuration to generate PromQL.",
    );
  }
  runButton.disabled = !currentPlan || !data;
}
function datasetChanged() {
  data = undefined;
  try {
    data = parseDataset(dataEditor.value);
    el("dataset-status").textContent =
      locale === "zh"
        ? `${data.length} 条序列 · ${data.reduce((n, s) => n + s.samples.length, 0)} 个样本 · 可以查询`
        : `${data.length} series · ${data.reduce((n, s) => n + s.samples.length, 0)} samples · ready to query`;
    const list = (id: string, values: string[]) =>
      el(id).replaceChildren(
        ...[...new Set(values)].map((v) => new Option(v, v)),
      );
    list(
      "lab-metrics",
      data.map((s) => s.metric),
    );
    list(
      "lab-labels",
      data.flatMap((s) => Object.keys(s.labels)),
    );
    list(
      "lab-values",
      data.flatMap((s) => Object.values(s.labels)),
    );
  } catch (e) {
    el("dataset-status").textContent = String(e);
  }
  update();
}
function labelText(labels: Record<string, string>): string {
  return `{${Object.entries(labels)
    .map(([k, v]) => `${k}=${JSON.stringify(v)}`)
    .join(", ")}}`;
}
const colors = [
  "#26745d",
  "#cf7243",
  "#5879be",
  "#a464aa",
  "#9b8526",
  "#27959c",
];
const ns = "http://www.w3.org/2000/svg";
function svgNode(tag: string, attrs: Record<string, string>, text = "") {
  const node = document.createElementNS(ns, tag);
  for (const [key, value] of Object.entries(attrs))
    node.setAttribute(key, value);
  node.textContent = text;
  return node;
}
function drawChart(
  selected: Plan,
  samples: Series[],
  end: number,
  matches: LabelPredicate,
) {
  const steps = Array.from(
    { length: Math.floor(end / 30) + 1 },
    (_, i) => i * 30,
  );
  if (steps.at(-1) !== end) steps.push(end);
  const series = new Map<string, Map<number, number>>();
  for (const t of steps)
    for (const sample of evaluate(selected, samples, t, matches)) {
      const key = labelText(sample.labels);
      if (!series.has(key)) series.set(key, new Map());
      series.get(key)!.set(t, sample.value);
    }
  const values = [...series.values()]
    .flatMap((s) => [...s.values()])
    .filter(Number.isFinite);
  const minimum = Math.min(0, ...values),
    maximum = Math.max(1, ...values);
  const x = (t: number) => 55 + (t / Math.max(end, 1)) * 820;
  const y = (v: number) => 205 - ((v - minimum) / (maximum - minimum)) * 180;
  const svg = svgNode("svg", {
    viewBox: "0 0 900 240",
    role: "img",
    "aria-label":
      locale === "zh"
        ? `从 0 到 ${end} 秒的模拟查询结果。即时值见下方表格。`
        : `Simulated query results from 0 to ${end} seconds. Instant values are in the table below.`,
  });
  for (let i = 0; i <= 3; i++) {
    const value = minimum + ((maximum - minimum) * i) / 3;
    svg.append(
      svgNode("line", {
        x1: "55",
        x2: "875",
        y1: String(y(value)),
        y2: String(y(value)),
        stroke: "var(--line)",
      }),
    );
    svg.append(
      svgNode(
        "text",
        { x: "47", y: String(y(value) + 4), "text-anchor": "end" },
        Number(value.toPrecision(3)).toString(),
      ),
    );
  }
  for (const t of [0, end / 2, end])
    svg.append(
      svgNode(
        "text",
        { x: String(x(t)), y: "229", "text-anchor": "middle" },
        `${t}s`,
      ),
    );
  const legend = document.createElement("div");
  legend.className = "chart-legend";
  let index = 0;
  for (const [key, points] of series) {
    const color = colors[index++ % colors.length];
    let path = "",
      connected = false;
    for (const t of steps) {
      const value = points.get(t);
      if (value === undefined || !Number.isFinite(value)) {
        connected = false;
        continue;
      }
      path += `${connected ? "L" : "M"}${x(t)},${y(value)} `;
      connected = true;
      svg.append(
        svgNode("circle", {
          cx: String(x(t)),
          cy: String(y(value)),
          r: "2",
          fill: color,
        }),
      );
    }
    svg.append(
      svgNode("path", {
        d: path,
        stroke: color,
        "stroke-width": "2",
        fill: "none",
      }),
    );
    const label = document.createElement("span");
    label.textContent = key;
    label.style.borderColor = color;
    legend.append(label);
  }
  el("result-chart").replaceChildren(svg, legend);
}
function execute() {
  if (!currentPlan || !data) return;
  const timeInput = el<HTMLInputElement>("lab-time");
  if (!timeInput.value || !timeInput.checkValidity()) {
    error.textContent = t(
      "Evaluation time must be an integer from 0 to 3600 seconds.",
    );
    clearResults(t("Invalid evaluation time."));
    return;
  }
  const time = Number(timeInput.value);
  const matches = compileMatchers(currentPlan.matchers);
  const result = evaluate(currentPlan, data, time, matches);
  el("result-rows").replaceChildren(
    ...result.map((sample) => {
      const row = document.createElement("tr"),
        labels = document.createElement("td"),
        value = document.createElement("td");
      labels.textContent = labelText(sample.labels);
      value.textContent = Number.isFinite(sample.value)
        ? Number(sample.value.toPrecision(8)).toString()
        : Number.isNaN(sample.value)
          ? "NaN"
          : sample.value > 0
            ? "+Inf"
            : "-Inf";
      row.append(labels, value);
      return row;
    }),
  );
  el("result-empty").hidden = result.length !== 0;
  drawChart(currentPlan, data, time, matches);
  el("result-status").textContent =
    locale === "zh"
      ? `${time} 秒时有 ${result.length} 条结果序列 · 本地模拟`
      : `${result.length} result series at ${time}s · simulated locally`;
  error.textContent = "";
}
form.addEventListener("input", update);
form.addEventListener("change", update);
form.addEventListener("submit", (event) => {
  event.preventDefault();
  execute();
});
el("add-filter").addEventListener("click", () => {
  addFilter();
  update();
  rows.lastElementChild?.querySelector("input")?.focus();
});
el("try-regex").addEventListener("click", () => {
  rows.replaceChildren();
  addFilter("instance", "=~", "api-.*");
  addFilter("environment", "!~", "staging|development");
  update();
});
dataEditor.addEventListener("input", datasetChanged);
el("lab-time").addEventListener("input", () => clearResults());
document
  .querySelectorAll<HTMLButtonElement>("[data-fixture]")
  .forEach((button) =>
    button.addEventListener("click", () => {
      const kind = button.dataset.fixture as "counter" | "gauge";
      dataEditor.value = JSON.stringify(fixture(kind), null, 2);
      field("metric").value =
        kind === "counter" ? "http_requests_total" : "queue_depth";
      field("rollup").value = kind === "counter" ? "rate" : "avg_over_time";
      datasetChanged();
    }),
  );
el("add-series").addEventListener("click", () => {
  if (!data || data.length >= 64) {
    el("dataset-status").textContent = t(
      "Fix the JSON first, and keep the dataset within 64 series.",
    );
    return;
  }
  const next = {
    metric: field("metric").value,
    labels: {
      service: "custom",
      instance: `custom-${Date.now()}`,
      environment: "production",
    },
    samples: [
      [0, 0],
      [300, 600],
      [600, 1200],
    ],
  };
  dataEditor.value = JSON.stringify([...data, next], null, 2);
  datasetChanged();
  dataEditor.focus();
});
document
  .querySelectorAll<HTMLButtonElement>("[data-copy-lab]")
  .forEach((button) =>
    button.addEventListener("click", async () => {
      const original = button.textContent;
      try {
        await navigator.clipboard.writeText(
          el(button.dataset.copyLab!).textContent || "",
        );
        button.textContent = t("Copied");
      } catch {
        button.textContent = t("Select code to copy");
      }
      setTimeout(() => (button.textContent = original), 1500);
    }),
  );
addFilter(initialPlan.matchers[0].label, "=", initialPlan.matchers[0].value);
dataEditor.value = JSON.stringify(fixture(), null, 2);
datasetChanged();
async function initialize() {
  try {
    const base = import.meta.env.BASE_URL.replace(/\/$/, "");
    const module = await import(
      /* @vite-ignore */ `${base}/playground-wasm/builder.js`
    );
    await module.default();
    build = module.build_query;
    runButton.textContent = t("Run query →");
    update();
    execute();
  } catch (e) {
    error.textContent = `${t("The Rust WebAssembly builder could not load. Reload to retry.")} ${String(e)}`;
    runButton.textContent = t("Builder unavailable");
    runButton.disabled = true;
  }
}
void initialize();
