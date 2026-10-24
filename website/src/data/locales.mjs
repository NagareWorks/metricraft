export const locales = ["en", "zh"];
export const languageNames = { en: "English", zh: "中文" };

export function localizedSource(source, locale) {
  if (locale === "en") return source;
  if (source === "CONTRIBUTING.md") return "docs/zh/contributing.md";
  if (source === "benchmarks/README.md") return "docs/zh/benchmarks.md";
  return source.replace(/^docs\//, "docs/zh/");
}

export function localizedPath(base, slug = "", locale = "en") {
  return `${base.replace(/\/$/, "")}/${locale}/${slug ? `${slug}/` : ""}`;
}
