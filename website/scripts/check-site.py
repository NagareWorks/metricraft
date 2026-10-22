"""Validate emitted local links, fragments and assets under the GitHub Pages base."""
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urlsplit

DIST = Path(__file__).resolve().parents[1] / "dist"
ROOT = DIST.parents[1]
BASE = "/metricraft/"


class Page(HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.ids = set()
        self.links = []
        self.duplicates = []
        self.signature_text = []
        self.in_signature = False
        self.feed(path.read_text(encoding="utf-8"))

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "pre" and "api-signature" in attrs.get("class", "").split():
            self.in_signature = True
        if "id" in attrs:
            if attrs["id"] in self.ids:
                self.duplicates.append(attrs["id"])
            self.ids.add(attrs["id"])
        for attr in ("href", "src"):
            if attrs.get(attr):
                self.links.append(attrs[attr])

    def handle_data(self, data):
        if self.in_signature:
            self.signature_text.append(data)

    def handle_endtag(self, tag):
        if tag == "pre":
            self.in_signature = False


def main():
    pages = {p.resolve(): Page(p) for p in DIST.rglob("*.html")}
    failures = []
    checked = 0
    for path, page in pages.items():
        if any(text != text.strip() for text in page.signature_text):
            failures.append(f"{path.name}: template whitespace in an API signature")
        failures.extend(f"{path.name}: duplicate id {value}" for value in page.duplicates)
        for link in page.links:
            url = urlsplit(link)
            if link.startswith("https://github.com/NagareWorks/metricraft/blob/main/"):
                source = unquote(url.path.split("/blob/main/", 1)[1])
                if not (ROOT / source).is_file():
                    failures.append(f"{path.name}: missing repository source {link}")
            if url.scheme or url.netloc:
                continue
            if url.path.startswith("/"):
                if not url.path.startswith(BASE):
                    failures.append(f"{path.name}: path outside Pages base {link}")
                    continue
                target = DIST / unquote(url.path[len(BASE):])
            elif not url.path:
                target = path
            else:
                target = path.parent / unquote(url.path)
            if target.is_dir():
                target /= "index.html"
            target = target.resolve()
            checked += 1
            if not target.is_file():
                failures.append(f"{path.relative_to(DIST)}: missing target {link}")
            elif url.fragment and target in pages and unquote(url.fragment) not in pages[target].ids:
                failures.append(f"{path.relative_to(DIST)}: missing fragment {link}")
    if not (DIST / "pagefind/pagefind.js").is_file():
        failures.append("Missing Pagefind search bundle")
    if not (DIST / "playground-wasm/builder_bg.wasm").is_file():
        failures.append("Missing real Rust playground builder")
    if len(pages) < 20:
        failures.append(f"Unexpected page count: {len(pages)}")
    if failures:
        raise SystemExit("\n".join(failures))
    print(f"Validated {len(pages)} HTML pages and {checked} local links/assets; all fragments and repository source links resolve.")


if __name__ == "__main__":
    main()
