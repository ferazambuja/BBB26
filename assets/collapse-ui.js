/* Shared mobile collapse/expand logic for cartola, provas, and future pages.
   Works on any page that contains .collapse-toggle[data-target] elements. */
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
    var title = document.querySelector("#quarto-header .navbar-title");
    if (!title) return;

    var fullTitle = title.dataset.fullTitle || title.textContent || "";
    title.dataset.fullTitle = fullTitle;
    title.textContent = isMobile() ? "BBB 26" : fullTitle;
  }

  function syncCollapseButtons() {
    var buttons = document.querySelectorAll(".collapse-toggle[data-target]");
    buttons.forEach(function (button) {
      var targetId = button.getAttribute("data-target");
      if (!targetId) return;

      var container = document.getElementById(targetId);
      if (!container) {
        button.hidden = true;
        return;
      }

      var extras = container.querySelectorAll(".collapse-extra");
      if (!extras.length) {
        button.hidden = true;
        return;
      }

      if (!isMobile()) {
        container.classList.remove("mobile-collapsed", "mobile-expanded");
        button.hidden = true;
        return;
      }

      button.hidden = false;

      var expanded = container.classList.contains("mobile-expanded");
      if (!expanded && !container.classList.contains("mobile-collapsed")) {
        container.classList.add("mobile-collapsed");
      }

      var isExpanded = container.classList.contains("mobile-expanded");
      var labelMore = button.getAttribute("data-label-more") || "Ver mais";
      var labelLess = button.getAttribute("data-label-less") || "Ver menos";
      button.textContent = isExpanded ? labelLess : labelMore;
    });
  }

  function bindCollapseHandlers() {
    var buttons = document.querySelectorAll(".collapse-toggle[data-target]");
    buttons.forEach(function (button) {
      button.addEventListener("click", function () {
        var targetId = button.getAttribute("data-target");
        if (!targetId) return;
        var container = document.getElementById(targetId);
        if (!container) return;

        var willExpand = !container.classList.contains("mobile-expanded");
        container.classList.toggle("mobile-expanded", willExpand);
        container.classList.toggle("mobile-collapsed", !willExpand);
        syncCollapseButtons();
      });
    });
  }

  function isSincSyncVisible(toggle) {
    return !toggle.closest(".sinc-more:not([open])");
  }

  function bindSinceraoToggleSync() {
    var cards = document.querySelectorAll("[data-sinc-sync-card]");
    cards.forEach(function (card) {
      var syncing = false;
      var toggles = card.querySelectorAll('.sinc-person-chip-toggle[data-sinc-sync-toggle="chooser"]');
      if (!toggles.length) return;

      toggles.forEach(function (toggle) {
        toggle.addEventListener("toggle", function () {
          if (syncing || !isSincSyncVisible(toggle)) return;

          syncing = true;
          var shouldOpen = toggle.open;
          toggles.forEach(function (otherToggle) {
            if (otherToggle === toggle || !isSincSyncVisible(otherToggle)) return;
            otherToggle.open = shouldOpen;
          });
          syncing = false;
        });
      });
    });
  }

  onReady(function () {
    var collapseToggles = document.querySelectorAll(".collapse-toggle[data-target]");
    var sincSyncCards = document.querySelectorAll("[data-sinc-sync-card]");

    if (collapseToggles.length) {
      syncNavbarTitle();
      bindCollapseHandlers();
      syncCollapseButtons();

      window.addEventListener("resize", function () {
        syncNavbarTitle();
        syncCollapseButtons();
      });
    }

    if (sincSyncCards.length) {
      bindSinceraoToggleSync();
    }
  });
})();
