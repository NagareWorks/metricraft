import path from "node:path";
import { fileURLToPath } from "node:url";
import { pages, repository } from "../src/data/navigation.mjs";

const root = fileURLToPath(new URL("../../", import.meta.url));
const bySource = new Map(pages.map((page) => [page.source, page.slug]));
export default function documentationLinks({ base = "/metricraft" } = {}) {
  return (tree, file) => {
    if (tree.children[0]?.type === "heading" && tree.children[0].depth === 1)
      tree.children.shift();
    const visit = (node) => {
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
            ? `${base}/${slug}/${fragment ? `#${fragment}` : ""}`
            : `${repository}/blob/main/${source}${fragment ? `#${fragment}` : ""}`;
      }
      node.children?.forEach(visit);
    };
    visit(tree);
  };
}
