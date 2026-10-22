import { defineConfig } from "astro/config";
import { unified } from "@astrojs/markdown-remark";
import documentationLinks from "./scripts/remark-docs.mjs";

export default defineConfig({
  site: "https://nagareworks.github.io",
  base: "/metricraft",
  trailingSlash: "always",
  output: "static",
  markdown: {
    processor: unified({
      remarkPlugins: [[documentationLinks, { base: "/metricraft" }]],
    }),
    shikiConfig: {
      themes: { light: "github-light", dark: "github-dark" },
      wrap: false,
    },
  },
  devToolbar: { enabled: false },
});
