# Documentation website

The English documentation lives in this repository. Astro provides static page
generation; the layout and styles are custom. Pagefind indexes the built pages
for local search. There is no application backend or external search service.

## Work locally

Use Node.js 24+, Python 3.11+ and Rust stable. The playground compiles the same
Rust core as the Python SDK into a browser-only WebAssembly module:

```sh
cd website
rustup target add wasm32-unknown-unknown
cargo install wasm-bindgen-cli --version 0.2.122 --locked
npm ci
npm run dev
```

Open the URL printed by Astro, including `/metricraft/`. For search and a faithful
production preview, build first:

```sh
npm run check
npm run build
python scripts/check-native.py  # requires promtool 3.15.0 on PATH
npm run preview
```

`check` runs Astro/TypeScript diagnostics. `build` generates the static site,
indexes search and verifies local links, fragments, assets and repository source
links. Both regenerate the API reference without importing the SDK. Building also
compiles WebAssembly and runs simulator tests. Set `CARGO_TARGET_DIR` to relocate
Rust artifacts if needed. The demo's isolated Cargo workspace is not a published
JavaScript SDK and does not add an execution engine to the Python package.

## Content and design

- Edit Markdown in `../docs/`; the website also reads `CONTRIBUTING.md` and the
  benchmark guide directly. No second copy of the content is maintained.
- Register pages and their navigation metadata in `src/data/navigation.mjs`.
- `scripts/remark-docs.mjs` converts repository-relative links into site links,
  retaining source-file links to GitHub. The page layout supplies the first H1.
- `scripts/generate-api.py` reads public declarations and requires purpose,
  parameter, constraint and return contracts from `scripts/api_*.py`. Add category
  introductions in `docs/reference/` and navigation in `src/data/api-categories.json`.
  Missing editorial contracts fail generation. Signatures/defaults always come
  from the source. Old method anchors redirect to the appropriate category.
- The playground shares a structured plan between the Rust builder, Python code
  renderer and a bounded docs-only float simulator. Tests compare snippets with
  the native Python SDK and the simulator with pinned Prometheus `promtool`.
  Result labels and cardinality must match exactly; finite values use a tolerance
  of `1e-12 * max(1, abs(expected))` to allow floating-point aggregation order.
  Unsupported evaluation semantics are listed in the UI; arbitrary text is not executed.
- Layouts, components and styles live in `src/`. Fonts are bundled locally.
- `.astro/`, `.generated/`, `dist/` and `node_modules/` are generated and ignored.

Keep keyboard navigation, search, themes and narrow screens working when changing
the layout. Verify a production preview, including a search result and an API
deep link. The link checker does not replace browser interaction checks.

## Deployment

The CI workflow checks the site on every pull request. `Documentation` deploys
from protected `main` to GitHub Pages at
<https://nagareworks.github.io/metricraft/>. Fork pull requests cannot deploy.
Repository Pages must use **GitHub Actions** as the source; the `github-pages`
environment must restrict deployment to `main`.

The site describes the development SDK. Update release/install guidance only
after native artifacts have been published and installed successfully.
