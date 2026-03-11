(function () {
  function normalizeWhitespace(text) {
    return String(text || "").replace(/\s+/g, " ").trim();
  }

  function dedupeTitleBlockDescription() {
    var titleBlock = document.querySelector("#title-block-header");
    if (!titleBlock) return;

    var subtitle = titleBlock.querySelector(".subtitle.lead");
    var description = titleBlock.querySelector(".description");
    if (!subtitle || !description) return;

    var subtitleText = normalizeWhitespace(subtitle.textContent);
    var descriptionText = normalizeWhitespace(description.textContent);

    if (!subtitleText || subtitleText !== descriptionText) return;

    description.hidden = true;
    description.setAttribute("aria-hidden", "true");
    titleBlock.dataset.dedupedDescription = "true";
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", dedupeTitleBlockDescription);
  } else {
    dedupeTitleBlockDescription();
  }
})();
