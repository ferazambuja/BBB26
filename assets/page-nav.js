// Unified bottom page navigation injected across pages.
document.addEventListener("DOMContentLoaded", () => {
  const main = document.querySelector("main.content");
  if (!main || document.querySelector(".page-nav-global")) return;

  const pages = [
    { file: "index.html", label: "Painel" },
    { file: "evolucao.html", label: "Evolução" },
    { file: "relacoes.html", label: "Relações" },
    { file: "paredao.html", label: "Paredão" },
    { file: "paredoes.html", label: "Paredões" },
    { file: "votacao.html", label: "Votação" },
    { file: "cartola.html", label: "Cartola" },
    { file: "provas.html", label: "Provas" },
    { file: "datas.html", label: "Datas" },
    { file: "clusters.html", label: "Clusters" },
    { file: "planta_debug.html", label: "Planta (debug)" },
    { file: "relacoes_debug.html", label: "Relações (debug)" },
  ];

  const corePages = new Set([
    "index.html",
    "evolucao.html",
    "relacoes.html",
    "paredao.html",
    "paredoes.html",
    "votacao.html",
    "cartola.html",
    "provas.html",
  ]);

  const currentPath = window.location.pathname.split("/").pop() || "index.html";
  const currentIndex = pages.findIndex((page) => page.file === currentPath);
  if (currentIndex === -1) return;

  const prev = currentIndex > 0 ? pages[currentIndex - 1] : null;
  const next = currentIndex < pages.length - 1 ? pages[currentIndex + 1] : null;

  const toAction = (page, direction) => {
    if (!page) {
      return `<span class="page-nav-action page-nav-action-disabled">${direction}</span>`;
    }
    return `<a class="page-nav-action" href="${page.file}">${direction}: ${page.label}</a>`;
  };

  const toChip = (page) => {
    const activeClass = page.file === currentPath ? " page-nav-chip-active" : "";
    return `<a class="page-nav-chip${activeClass}" href="${page.file}">${page.label}</a>`;
  };

  const coreLinks = pages.filter((page) => corePages.has(page.file)).map(toChip).join("");
  const extraLinks = pages.filter((page) => !corePages.has(page.file)).map(toChip).join("");

  const wrapper = document.createElement("section");
  wrapper.className = "page-nav-global";
  wrapper.setAttribute("aria-label", "Navegação entre páginas");
  wrapper.innerHTML = `
    <h2 class="page-nav-title">Explorar páginas</h2>
    <p class="page-nav-subtitle">Navegação rápida entre análises do BBB 26.</p>
    <div class="page-nav-actions">
      ${toAction(prev, "Anterior")}
      ${toAction(next, "Próxima")}
    </div>
    <p class="page-nav-section-label">Páginas principais</p>
    <div class="page-nav-links">${coreLinks}</div>
    <p class="page-nav-section-label">Mais análises</p>
    <div class="page-nav-links">${extraLinks}</div>
  `;

  main.appendChild(wrapper);
});
