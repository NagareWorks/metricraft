import { translator } from "../data/translate";

const figures = [...document.querySelectorAll<HTMLElement>("[data-diagram]")];
if (figures.length) {
  const t = translator(
    document.documentElement.lang.startsWith("zh") ? "zh" : "en",
  );
  const renderer = import("mermaid");
  const updateOverflow = () => {
    for (const figure of figures) {
      const canvas = figure.querySelector<HTMLElement>(
        "[data-diagram-canvas]",
      )!;
      figure.querySelector<HTMLElement>("[data-diagram-hint]")!.hidden =
        canvas.scrollWidth <= canvas.clientWidth + 1;
    }
  };
  const observer = new ResizeObserver(updateOverflow);
  figures.forEach((figure) =>
    observer.observe(figure.querySelector("[data-diagram-canvas]")!),
  );
  let revision = 0;
  let queue = Promise.resolve();
  function refresh() {
    const requested = ++revision;
    queue = queue
      .then(async () => {
        if (requested !== revision) return;
        const { default: mermaid } = await renderer;
        await document.fonts.ready;
        const dark = document.documentElement.dataset.theme === "dark";
        mermaid.initialize({
          startOnLoad: false,
          securityLevel: "strict",
          theme: "base",
          look: "classic",
          fontFamily: 'Manrope, "PingFang SC", "Microsoft YaHei", sans-serif',
          flowchart: {
            htmlLabels: false,
            curve: "linear",
            padding: 14,
            nodeSpacing: 25,
            rankSpacing: 35,
            wrappingWidth: 150,
          },
          themeVariables: {
            primaryColor: dark ? "#203d34" : "#edf5ef",
            primaryTextColor: dark ? "#e4efe7" : "#193c31",
            primaryBorderColor: dark ? "#689c86" : "#80aa96",
            lineColor: dark ? "#a5bcaf" : "#5f7a6a",
            secondaryColor: dark ? "#253b43" : "#edf3f5",
            tertiaryColor: dark ? "#26332d" : "#f8f7f0",
            clusterBkg: dark ? "#1a2923" : "#fafbf7",
            clusterBorder: dark ? "#456454" : "#ccdacd",
            edgeLabelBackground: dark ? "#17241e" : "#fafbf7",
          },
        });
        for (const [index, figure] of figures.entries()) {
          if (requested !== revision) return;
          const source = figure.querySelector<HTMLElement>(
            "[data-diagram-source]",
          )!.textContent!;
          const canvas = figure.querySelector<HTMLElement>(
            "[data-diagram-canvas]",
          )!;
          const { svg } = await mermaid.render(
            `diagram-${index}-${requested}`,
            source,
          );
          if (requested !== revision) return;
          canvas.innerHTML = svg;
          const drawing = canvas.querySelector("svg")!;
          // Keep labels readable; a narrow screen can scroll the diagram itself.
          drawing.style.width = `${drawing.viewBox.baseVal.width}px`;
          drawing.style.maxWidth = "none";
          drawing.style.height = "auto";
          canvas.setAttribute(
            "aria-label",
            source.match(/^\s*accTitle:\s*(.+)$/m)?.[1] || t("Diagram"),
          );
          figure.dataset.diagramReady = "true";
          updateOverflow();
        }
      })
      .catch(() => {
        for (const figure of figures) {
          if (!figure.dataset.diagramReady) {
            figure.querySelector("[data-diagram-canvas]")!.textContent = t(
              "The diagram could not load. Read the explanation below.",
            );
            figure.dataset.diagramError = "true";
          }
        }
      });
  }
  new MutationObserver(refresh).observe(document.documentElement, {
    attributes: true,
    attributeFilter: ["data-theme"],
  });
  refresh();
}
