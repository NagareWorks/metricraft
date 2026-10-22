import { pages } from "../data/navigation.mjs";
export function GET() {
  const urls = ["", ...pages.map((page) => `${page.slug}/`)];
  return new Response(
    `<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">${urls.map((path) => `<url><loc>https://nagareworks.github.io/metricraft/${path}</loc></url>`).join("")}</urlset>`,
    { headers: { "Content-Type": "application/xml" } },
  );
}
