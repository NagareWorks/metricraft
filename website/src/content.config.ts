import { defineCollection } from "astro:content";
import { glob } from "astro/loaders";

const docs = defineCollection({
  loader: glob({
    pattern: ["docs/**/*.md", "benchmarks/README.md", "CONTRIBUTING.md"],
    base: "..",
    generateId: ({ entry }) => entry.replace(/\.md$/, ""),
  }),
});
export const collections = { docs };
