(function () {
  function onReady(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
      return;
    }
    fn();
  }

  function isMobile() {
    return window.matchMedia("(max-width: 575.98px)").matches;
  }

  function syncNavbarTitle() {
    const title = document.querySelector("#quarto-header .navbar-title");
    if (!title) return;

    const fullTitle = title.dataset.fullTitle || title.textContent || "";
    title.dataset.fullTitle = fullTitle;
    title.textContent = isMobile() ? "BBB 26" : fullTitle;
  }

  function syncCollapseButtons() {
    const buttons = document.querySelectorAll(".provas-collapse-toggle[data-target]");
    buttons.forEach((button) => {
      const targetId = button.getAttribute("data-target");
      if (!targetId) return;

      const container = document.getElementById(targetId);
      if (!container) {
        button.hidden = true;
        return;
      }

      const extras = container.querySelectorAll(".provas-collapse-extra");
      if (!extras.length) {
        button.hidden = true;
        return;
      }

      if (!isMobile()) {
        container.classList.remove("provas-mobile-collapsed", "provas-mobile-expanded");
        button.hidden = true;
        return;
      }

      button.hidden = false;

      const expanded = container.classList.contains("provas-mobile-expanded");
      if (!expanded && !container.classList.contains("provas-mobile-collapsed")) {
        container.classList.add("provas-mobile-collapsed");
      }

      const isExpanded = container.classList.contains("provas-mobile-expanded");
      const labelMore = button.getAttribute("data-label-more") || "Ver mais";
      const labelLess = button.getAttribute("data-label-less") || "Ver menos";
      button.textContent = isExpanded ? labelLess : labelMore;
    });
  }

  function bindCollapseHandlers() {
    const buttons = document.querySelectorAll(".provas-collapse-toggle[data-target]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const targetId = button.getAttribute("data-target");
        if (!targetId) return;

        const container = document.getElementById(targetId);
        if (!container) return;

        const willExpand = !container.classList.contains("provas-mobile-expanded");
        container.classList.toggle("provas-mobile-expanded", willExpand);
        container.classList.toggle("provas-mobile-collapsed", !willExpand);
        syncCollapseButtons();
      });
    });
  }

  onReady(() => {
    const provasMarker = document.querySelector("#provas-page");
    if (!provasMarker) return;

    document.body.classList.add("provas-page");

    syncNavbarTitle();
    bindCollapseHandlers();
    syncCollapseButtons();

    window.addEventListener("resize", () => {
      syncNavbarTitle();
      syncCollapseButtons();
    });
  });
})();
