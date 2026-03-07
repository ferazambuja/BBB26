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
    const buttons = document.querySelectorAll(".cartola-collapse-toggle[data-target]");
    buttons.forEach((button) => {
      const targetId = button.getAttribute("data-target");
      if (!targetId) return;

      const container = document.getElementById(targetId);
      if (!container) {
        button.hidden = true;
        return;
      }

      const extras = container.querySelectorAll(".cartola-collapse-extra");
      if (!extras.length) {
        button.hidden = true;
        return;
      }

      if (!isMobile()) {
        container.classList.remove("cartola-mobile-collapsed", "cartola-mobile-expanded");
        button.hidden = true;
        return;
      }

      button.hidden = false;

      const expanded = container.classList.contains("cartola-mobile-expanded");
      if (!expanded && !container.classList.contains("cartola-mobile-collapsed")) {
        container.classList.add("cartola-mobile-collapsed");
      }

      const isExpanded = container.classList.contains("cartola-mobile-expanded");
      const labelMore = button.getAttribute("data-label-more") || "Ver mais";
      const labelLess = button.getAttribute("data-label-less") || "Ver menos";
      button.textContent = isExpanded ? labelLess : labelMore;
    });
  }

  function bindCollapseHandlers() {
    const buttons = document.querySelectorAll(".cartola-collapse-toggle[data-target]");
    buttons.forEach((button) => {
      button.addEventListener("click", () => {
        const targetId = button.getAttribute("data-target");
        if (!targetId) return;
        const container = document.getElementById(targetId);
        if (!container) return;

        const willExpand = !container.classList.contains("cartola-mobile-expanded");
        container.classList.toggle("cartola-mobile-expanded", willExpand);
        container.classList.toggle("cartola-mobile-collapsed", !willExpand);
        syncCollapseButtons();
      });
    });
  }

  onReady(() => {
    const cartolaMarker = document.querySelector("#cartola-page");
    if (!cartolaMarker) return;

    document.body.classList.add("cartola-page");

    syncNavbarTitle();
    bindCollapseHandlers();
    syncCollapseButtons();

    window.addEventListener("resize", () => {
      syncNavbarTitle();
      syncCollapseButtons();
    });
  });
})();
