# Documentation website

The English and Chinese documentation live in this repository. Astro provides static page
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

- Edit English Markdown in `../docs/` and Chinese Markdown in `../docs/zh/`.
  The website also reads `CONTRIBUTING.md` and the benchmark guide directly;
  their translations are `docs/zh/contributing.md` and `docs/zh/benchmarks.md`.
  The website does not keep separate copies of these Markdown sources.
- Register pages and their navigation metadata in `src/data/navigation.mjs`.
  Add matching Chinese titles/descriptions in `src/data/navigation.zh.json`.
- Explicit `/en/` and `/zh/` URLs determine the page language. Original URLs
  remain readable English fallbacks without JavaScript and redirect in the browser
  using a saved manual preference, otherwise the browser's primary language:
  `zh` and `zh-*` select Chinese; every other language selects English.
  The language switcher preserves the page, query string and fragment. Storage
  is optional; explicit language links work when it is unavailable.
- Chinese headings have an explicit `<a id="english-anchor"></a>` immediately
  before them so links work on GitHub as well as on the site. Existing deep links and language
  switches address the same section. Relative Markdown links resolve to the current
  language; source-code links still point to the real repository files.
- Interface translations live in `src/data/ui.zh.json`. Generated API translations
  live in `scripts/api_purposes_zh.py`, `api_parameters_zh.py` and
  `api_localization.py`. New API contracts are maintained in English; existing
  translations remain, and untranslated contracts use the English source. Names,
  signatures, defaults and executable examples stay identical across languages.
  Pagefind indexes each explicit language separately; legacy aliases are excluded.
- Use fenced `mermaid` blocks for relationships and workflows, with `accTitle`
  and `accDescr` in each language. Keep a short explanation alongside each diagram.
  The local Mermaid bundle loads only on pages with diagrams, renders in strict
  mode and follows the color theme. Diagrams can scroll within narrow screens.
  The build checks both languages with Mermaid's parser, using jsdom only for
  the parser's label sanitization; it is not shipped to the browser.
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
