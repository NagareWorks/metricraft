/** Check the emitted pages and real redirect script, including storage failures. */
import assert from "node:assert/strict";
import { readFileSync, readdirSync, existsSync } from "node:fs";
import vm from "node:vm";

const dist = new URL("../dist/", import.meta.url);
const read = (path) => readFileSync(new URL(path, dist), "utf8");
const files = readdirSync(new URL("en/", dist), { recursive: true })
  .map((path) => path.replaceAll("\\", "/"))
  .filter((path) => path.endsWith("index.html"));
assert.ok(files.length > 20, "The complete English site must be built first");
const ids = (html) =>
  [...html.matchAll(/\bid="([^"]+)"/g)].map((m) => m[1]).sort();
const examples = (html) =>
  [...html.matchAll(/<pre\b([^>]*)>([\s\S]*?)<\/pre>/g)]
    .filter(
      (m) => !/id="(?:python|promql)-output"|data-diagram-source/.test(m[1]),
    )
    .map((m) => m[2]);

function redirect(
  html,
  {
    saved,
    languages,
    language = "en-US",
    blocked = false,
    pathname = "/metricraft/",
  } = {},
) {
  const script = [
    ...html.matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g),
  ].find(
    (m) =>
      m[1].includes("metricraft-language") && m[1].includes("location.replace"),
  )?.[1];
  assert.ok(script, "The real language redirect script must be present");
  let target;
  vm.runInNewContext(script, {
    navigator: { language, languages },
    localStorage: {
      getItem() {
        if (blocked) throw new Error("Storage disabled");
        return saved;
      },
    },
    location: {
      pathname,
      search: "?source=test",
      hash: "#compose-a-query",
      replace(value) {
        target = value;
      },
    },
  });
  return target;
}

for (const path of files) {
  const english = read(`en/${path}`),
    chinese = read(`zh/${path}`);
  assert.match(english, /<html lang="en"/);
  assert.match(chinese, /<html lang="zh-CN"/);
  assert.deepEqual(
    ids(chinese),
    ids(english),
    `Language switches must preserve every anchor: ${path}`,
  );
  assert.deepEqual(
    examples(chinese),
    examples(english),
    `Copied code must stay identical: ${path}`,
  );
  assert.ok(
    !/Migrate existing code|迁移已有代码|Rust migration status|Rust 迁移状态/.test(
      english + chinese,
    ),
  );
  const route = path.replace(/index\.html$/, "");
  assert.ok(
    english.includes(`href="/metricraft/zh/${route}"`),
    `Missing Chinese switch: ${path}`,
  );
  assert.ok(
    chinese.includes(`href="/metricraft/en/${route}"`),
    `Missing English switch: ${path}`,
  );
  assert.equal(
    redirect(english, { saved: "zh", languages: ["zh-CN"] }),
    undefined,
    "Explicit English URLs win",
  );
  assert.equal(
    redirect(chinese, { saved: "en", languages: ["en-US"] }),
    undefined,
    "Explicit Chinese URLs win",
  );
  if (path === "404/index.html") continue;
  assert.ok(existsSync(new URL(path, dist)), `Missing original URL: ${path}`);
  const alias = read(path);
  assert.match(alias, /data-pagefind-ignore="all"/);
  assert.match(alias, /name="robots" content="noindex"/);
  for (const browserLanguage of [
    "zh",
    "zh-CN",
    "zh-TW",
    "zh-Hant",
    "ZH-hk",
    "en-US",
    "ja",
    "fr",
    "de",
    "",
  ]) {
    const locale = /^zh(?:-|$)/i.test(browserLanguage) ? "zh" : "en";
    const expected = `/metricraft/${locale}/${route}?source=test#compose-a-query`;
    assert.equal(redirect(alias, { languages: [browserLanguage] }), expected);
    assert.equal(
      redirect(alias, { language: browserLanguage, blocked: true }),
      expected,
    );
  }
  assert.equal(
    redirect(alias, { languages: ["fr", "zh-CN"] }),
    `/metricraft/en/${route}?source=test#compose-a-query`,
  );
  assert.equal(
    redirect(alias, { saved: "en", languages: ["zh-CN"] }),
    `/metricraft/en/${route}?source=test#compose-a-query`,
  );
  assert.equal(
    redirect(alias, { saved: "zh", languages: ["en-US"] }),
    `/metricraft/zh/${route}?source=test#compose-a-query`,
  );
  assert.equal(
    redirect(alias, { saved: "invalid", languages: ["zh-CN"] }),
    `/metricraft/zh/${route}?source=test#compose-a-query`,
  );
}
assert.equal(
  redirect(read("404.html"), {
    pathname: "/metricraft/zh/missing/",
    saved: "en",
  }),
  "/metricraft/zh/404/?source=test#compose-a-query",
);
assert.equal(
  redirect(read("404.html"), {
    pathname: "/metricraft/en/missing/",
    saved: "zh",
  }),
  "/metricraft/en/404/?source=test#compose-a-query",
);
for (const path of [
  "reference/migration/index.html",
  "internals/rust-migration/index.html",
]) {
  for (const prefix of ["", "en/", "zh/"])
    assert.ok(
      !existsSync(new URL(prefix + path, dist)),
      `Removed page still emitted: ${prefix}${path}`,
    );
}

const api = (name) =>
  JSON.parse(
    readFileSync(new URL(`../.generated/${name}`, import.meta.url), "utf8"),
  );
const englishApi = api("api.json"),
  chineseApi = api("api.zh.json");
assert.equal(chineseApi.length, englishApi.length);
for (let c = 0; c < englishApi.length; c++) {
  assert.equal(chineseApi[c].name, englishApi[c].name);
  assert.equal(chineseApi[c].methods.length, englishApi[c].methods.length);
  for (let m = 0; m < englishApi[c].methods.length; m++) {
    const en = englishApi[c].methods[m],
      zh = chineseApi[c].methods[m];
    for (const key of [
      "id",
      "name",
      "signature",
      "source",
      "line",
      "badges",
      "example",
    ])
      assert.deepEqual(zh[key], en[key]);
    // New API contracts are maintained in English; existing translations remain.
    if (zh.purpose !== en.purpose) assert.match(zh.purpose, /[\u3400-\u9fff]/);
    const dialect = en.badges.includes("prom_only")
      ? "PromQL"
      : en.badges.includes("vm_only")
        ? "MetricsQL"
        : undefined;
    if (dialect) {
      for (const locale of ["en", "zh"]) {
        const page = read(`${locale}/reference/api/${en.category}/index.html`);
        const start = page.indexOf(`id="${en.id}"`);
        const summary = page.slice(start, page.indexOf("</summary>", start));
        assert.ok(
          summary.includes(
            locale === "zh" ? `仅限 ${dialect}` : `${dialect} only`,
          ),
          `Missing visible dialect badge: ${locale} ${en.id}`,
        );
      }
    }
    assert.equal(zh.parameters.length, en.parameters.length);
    zh.parameters.forEach((p, i) => {
      for (const key of ["name", "display", "default"])
        assert.equal(p[key], en.parameters[i][key]);
      if (p.description !== en.parameters[i].description)
        assert.match(p.description, /[\u3400-\u9fff]/);
    });
  }
}
console.log(
  `Verified ${files.length} page pairs, redirect/preferences/storage fallbacks, shared anchors/code, removed pages and translated or English-fallback API contracts.`,
);

// Mermaid's strict parser sanitizes labels and therefore needs a DOM even when
// validating syntax without rendering SVG. Browser rendering is checked separately.
const { JSDOM } = await import("jsdom");
const dom = new JSDOM("");
Object.defineProperty(globalThis, "window", { value: dom.window });
Object.defineProperty(globalThis, "document", { value: dom.window.document });
const { default: mermaid } = await import("mermaid");
mermaid.initialize({
  startOnLoad: false,
  securityLevel: "strict",
  flowchart: { htmlLabels: false },
});
const decode = dom.window.document.createElement("textarea");
let diagramCount = 0;
for (const path of files) {
  const sources = (locale) =>
    [
      ...read(`${locale}/${path}`).matchAll(
        /<pre\b[^>]*data-diagram-source[^>]*>([\s\S]*?)<\/pre>/g,
      ),
    ].map((m) => m[1]);
  const english = sources("en"),
    chinese = sources("zh");
  assert.equal(
    chinese.length,
    english.length,
    `Missing translated diagram: ${path}`,
  );
  for (const encoded of [...english, ...chinese]) {
    decode.innerHTML = encoded;
    const source = decode.value;
    assert.match(
      source,
      /accTitle:/,
      `Missing accessible diagram title: ${path}`,
    );
    assert.match(
      source,
      /accDescr:/,
      `Missing accessible diagram description: ${path}`,
    );
    assert.ok(await mermaid.parse(source), `Invalid Mermaid source: ${path}`);
    diagramCount++;
  }
}
dom.window.close();
assert.ok(diagramCount > 0, "Expected explanatory Mermaid diagrams");
console.log(
  `Validated ${diagramCount} localized Mermaid diagrams with the production parser.`,
);
