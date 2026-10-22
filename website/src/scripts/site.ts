const root = document.documentElement;
const themeButton = document.querySelector<HTMLButtonElement>("#theme-toggle");
function themeLabel() {
  themeButton?.setAttribute(
    "aria-label",
    `Switch to ${root.dataset.theme === "dark" ? "light" : "dark"} theme`,
  );
}
themeLabel();
themeButton?.addEventListener("click", () => {
  root.dataset.theme = root.dataset.theme === "dark" ? "light" : "dark";
  try {
    localStorage.setItem("metricraft-theme", root.dataset.theme);
  } catch {
    /* Preference storage is optional. */
  }
  themeLabel();
});

const search = document.querySelector<HTMLDialogElement>("#search-dialog")!;
const menu = document.querySelector<HTMLDialogElement>("#mobile-navigation")!;
const input = document.querySelector<HTMLInputElement>("#search-input")!;
const status = document.querySelector<HTMLElement>("#search-status")!;
const results = document.querySelector<HTMLOListElement>("#search-results")!;
const base = import.meta.env.BASE_URL.replace(/\/$/, "");
let opener: HTMLElement | null = null;
function openDialog(dialog: HTMLDialogElement) {
  if (dialog.open) return;
  opener = document.activeElement as HTMLElement;
  document
    .querySelectorAll<HTMLDialogElement>("dialog[open]")
    .forEach((other) => other.close());
  dialog.showModal();
  document.body.classList.add("dialog-open");
  if (dialog === search) input.focus();
}
document
  .querySelectorAll<HTMLButtonElement>("[data-search-open]")
  .forEach((button) =>
    button.addEventListener("click", () => openDialog(search)),
  );
document
  .querySelector("#menu-open")
  ?.addEventListener("click", () => openDialog(menu));
document.querySelectorAll<HTMLDialogElement>("dialog").forEach((dialog) => {
  dialog
    .querySelector("[data-close-dialog]")
    ?.addEventListener("click", () => dialog.close());
  dialog.addEventListener("click", (event) => {
    if (event.target === dialog) {
      const box = dialog.getBoundingClientRect();
      if (
        event.clientX < box.left ||
        event.clientX > box.right ||
        event.clientY < box.top ||
        event.clientY > box.bottom
      )
        dialog.close();
    }
  });
  dialog.addEventListener("close", () => {
    if (!document.querySelector("dialog[open]")) {
      document.body.classList.remove("dialog-open");
      opener?.focus();
    }
  });
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && (search.open || menu.open)) {
    event.preventDefault();
    (search.open ? search : menu).close();
    return;
  }
  if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
    event.preventDefault();
    openDialog(search);
  }
});
if (!/Mac|iPhone|iPad/.test(navigator.userAgent))
  document
    .querySelectorAll(".search-trigger kbd")
    .forEach((key) => (key.textContent = "Ctrl K"));

interface SearchPage {
  url: string;
  meta: { title?: string };
  excerpt: string;
}
interface SearchIndex {
  search: (
    query: string,
  ) => Promise<{ results: { data: () => Promise<SearchPage> }[] }>;
}
let pagefind: Promise<SearchIndex> | undefined;
let revision = 0;
let timer: ReturnType<typeof setTimeout>;
input.addEventListener("input", () => {
  const current = ++revision;
  clearTimeout(timer);
  const query = input.value.trim();
  results.replaceChildren();
  if (!query) {
    status.textContent = "Search guides, examples and the Python API.";
    return;
  }
  status.textContent = "Searching…";
  timer = setTimeout(async () => {
    try {
      pagefind ??= import(/* @vite-ignore */ `${base}/pagefind/pagefind.js`);
      const index = await pagefind;
      const found = await index.search(query);
      const matches = await Promise.all(
        found.results.slice(0, 12).map((result) => result.data()),
      );
      if (current !== revision) return;
      status.textContent = found.results.length
        ? `${found.results.length} matching page${found.results.length === 1 ? "" : "s"}.`
        : "No matching pages. Try a method name or a shorter phrase.";
      for (const page of matches) {
        const url = new URL(page.url, location.origin);
        if (
          url.origin !== location.origin ||
          !url.pathname.startsWith(`${base}/`)
        )
          continue;
        const item = document.createElement("li");
        const link = document.createElement("a");
        link.href = url.href;
        const title = document.createElement("strong");
        title.textContent = page.meta.title || "MetriCraft documentation";
        const excerpt = document.createElement("p");
        const parsed = new DOMParser().parseFromString(
          page.excerpt,
          "text/html",
        );
        excerpt.textContent = parsed.body.textContent;
        link.append(title, excerpt);
        item.append(link);
        results.append(item);
      }
    } catch {
      pagefind = undefined;
      if (current === revision)
        status.textContent =
          "Search could not load. Please retry, or use the navigation. Local previews need a full site build first.";
    }
  }, 150);
});
input.addEventListener("keydown", (event) => {
  if (event.key === "ArrowDown") {
    results.querySelector("a")?.focus();
    event.preventDefault();
  }
});
results.addEventListener("keydown", (event) => {
  const links = [...results.querySelectorAll("a")];
  const index = links.indexOf(document.activeElement as HTMLAnchorElement);
  if (event.key === "ArrowDown") {
    links[Math.min(index + 1, links.length - 1)]?.focus();
    event.preventDefault();
  }
  if (event.key === "ArrowUp") {
    if (index <= 0) input.focus();
    else links[index - 1].focus();
    event.preventDefault();
  }
});

document
  .querySelectorAll<HTMLPreElement>("pre:not([data-no-copy])")
  .forEach((pre) => {
    const code =
      pre.querySelector("code") ||
      (pre.hasAttribute("data-copy-plain") ? pre : null);
    if (!code) return;
    const wrapper = document.createElement("div");
    wrapper.className = "code-block";
    pre.replaceWith(wrapper);
    wrapper.append(pre);
    const button = document.createElement("button");
    button.type = "button";
    button.className = "copy-code";
    button.textContent = "Copy";
    button.setAttribute("aria-label", "Copy code");
    button.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(code.textContent || "");
        button.textContent = "Copied";
      } catch {
        button.textContent = "Select to copy";
        const selection = window.getSelection();
        const range = document.createRange();
        range.selectNodeContents(code);
        selection?.removeAllRanges();
        selection?.addRange(range);
      }
      setTimeout(() => (button.textContent = "Copy"), 1800);
    });
    wrapper.append(button);
  });

const apiFilter = document.querySelector<HTMLInputElement>("#api-filter");
function filterApi() {
  const query = apiFilter?.value.toLowerCase().trim() || "";
  let count = 0;
  document
    .querySelectorAll<HTMLElement>("[data-api-entry]")
    .forEach((entry) => {
      entry.hidden = !entry.dataset.filter?.includes(query);
      if (!entry.hidden) count++;
    });
  document
    .querySelectorAll<HTMLElement>("[data-api-class]")
    .forEach(
      (group) =>
        (group.hidden = !group.querySelector("[data-api-entry]:not([hidden])")),
    );
  const status = document.querySelector("#api-status");
  if (status)
    status.textContent = `${count} matching ${count === 1 ? "entry" : "entries"}`;
}
apiFilter?.addEventListener("input", filterApi);
if (apiFilter) filterApi();
function revealAnchor() {
  let id: string;
  try {
    id = decodeURIComponent(location.hash.slice(1));
  } catch {
    return;
  }
  const target = document.getElementById(id);
  if (
    target instanceof HTMLAnchorElement &&
    target.hasAttribute("data-api-redirect")
  ) {
    location.replace(target.href);
    return;
  }
  if (target?.closest("[data-api-class]") && apiFilter) {
    apiFilter.value = "";
    filterApi();
    target.scrollIntoView();
  }
  if (target instanceof HTMLDetailsElement) {
    if (apiFilter) {
      apiFilter.value = "";
      filterApi();
    }
    target.open = true;
    target.scrollIntoView();
  }
}
window.addEventListener("hashchange", revealAnchor);
revealAnchor();
