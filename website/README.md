# Documentation website

The English documentation lives in this repository. Astro provides static page
generation; the layout and styles are custom. Pagefind indexes the built pages
for local search. There is no application backend or external search service.

## Work locally

Use Node.js 24+ and Python 3.11+ (only its standard library is needed):

```sh
cd website
npm ci
npm run dev
```

Open the URL printed by Astro, including `/metricraft/`. For search and a faithful
production preview, build first:

```sh
npm run check
npm run build
npm run preview
```

`check` runs Astro/TypeScript diagnostics. `build` generates the static site,
indexes search and verifies local links, fragments, assets and repository source
links. Both regenerate the API signature index without importing the SDK.

## Content and design

- Edit Markdown in `../docs/`; the website also reads `CONTRIBUTING.md` and the
  benchmark guide directly. No second copy of the content is maintained.
- Register pages and their navigation metadata in `src/data/navigation.mjs`.
- `scripts/remark-docs.mjs` converts repository-relative links into site links,
  retaining source-file links to GitHub. The page layout supplies the first H1.
- `scripts/generate-api.py` reads public builder, client and configuration
  declarations using Python's AST. Generated signatures are a navigation aid;
  dialect acceptance remains the native builder's responsibility.
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
