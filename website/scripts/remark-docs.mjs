import path from "node:path";
import { fileURLToPath } from "node:url";
import { pages, repository } from "../src/data/navigation.mjs";
import { localizedSource, localizedPath } from "../src/data/locales.mjs";

const root = fileURLToPath(new URL("../../", import.meta.url));
const bySource = new Map(
  pages.flatMap((page) => [
    [page.source, page.slug],
    [localizedSource(page.source, "zh"), page.slug],
  ]),
);
export default function documentationLinks({ base = "/metricraft" } = {}) {
  return (tree, file) => {
    const locale = String(file.path).replaceAll("\\", "/").includes("/docs/zh/")
      ? "zh"
      : "en";
    if (tree.children[0]?.type === "heading" && tree.children[0].depth === 1)
      tree.children.shift();
    const visit = (node) => {
      // Explicit anchors also work when the Markdown is read directly on GitHub.
      // Transfer them to headings on the website so the TOC uses the same IDs.
      for (let index = (node.children?.length || 0) - 2; index >= 0; index--) {
        const marker = node.children[index];
        const heading = node.children[index + 1];
        const raw =
          marker.type === "html"
            ? marker.value
            : marker.type === "paragraph" &&
                marker.children.every((child) => child.type === "html")
              ? marker.children.map((child) => child.value).join("")
              : "";
        const anchor = raw.match(/^<a id="([a-z\d_-]+)"><\/a>$/i);
        if (anchor && heading.type === "heading") {
          heading.data = {
            ...heading.data,
            hProperties: { ...heading.data?.hProperties, id: anchor[1] },
          };
          node.children.splice(index, 1);
        }
      }
      if (node.type === "code" && node.lang === "mermaid") {
        const escape = (text) =>
          text
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;");
        const source = escape(node.value);
        const loading = locale === "zh" ? "正在加载图示…" : "Loading diagram…";
        const fallback =
          locale === "zh"
            ? "图示需要 JavaScript，下方文字说明仍可阅读。"
            : "Diagrams need JavaScript; the explanation below remains available.";
        const hint =
          locale === "zh"
            ? "左右滑动，查看完整图示"
            : "Scroll horizontally to see the whole diagram";
        node.type = "html";
        node.value = `<figure class="diagram" data-diagram data-pagefind-ignore><figcaption class="diagram-hint" data-diagram-hint hidden>${hint}</figcaption><div class="diagram-canvas" data-diagram-canvas tabindex="0"><p>${loading}</p></div><pre data-diagram-source data-no-copy hidden>${source}</pre><noscript><p>${fallback}</p></noscript></figure>`;
      }
      if (node.type === "code" && node.lang === "promql") node.lang = "text";
      if (
        ["link", "definition", "image"].includes(node.type) &&
        node.url &&
        !/^(?:[a-z][a-z\d+.-]*:|\/\/|#)/i.test(node.url)
      ) {
        const [target, fragment] = node.url.split("#");
        const absolute = path.resolve(
          path.dirname(String(file.path)),
          decodeURI(target),
        );
        const source = path.relative(root, absolute).replaceAll("\\", "/");
        const slug = bySource.get(source);
        node.url =
          slug !== undefined
            ? `${localizedPath(base, slug, locale)}${fragment ? `#${fragment}` : ""}`
            : `${repository}/blob/main/${source}${fragment ? `#${fragment}` : ""}`;
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}
