import { pages } from "../data/navigation.mjs";
import { locales, localizedPath } from "../data/locales.mjs";
export function GET() {
  const slugs = ["", ...pages.map((page) => page.slug)];
  const url = (slug: string, locale: string) =>
    `https://nagareworks.github.io${localizedPath("/metricraft", slug, locale)}`;
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9" xmlns:xhtml="http://www.w3.org/1999/xhtml">${slugs.flatMap((slug) => locales.map((locale) => `<url><loc>${url(slug, locale)}</loc>${locales.map((language) => `<xhtml:link rel="alternate" hreflang="${language === "zh" ? "zh-CN" : "en"}" href="${url(slug, language)}"/>`).join("")}</url>`)).join("")}</urlset>`,
    { headers: { "Content-Type": "application/xml" } },
  );
}
