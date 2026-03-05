// Mobile-first adaptations for dense/wide tables.
// Converts wide tables to compact card views on phones while keeping
// the original table available on demand.

(() => {
  const isMobile = () => window.matchMedia("(max-width: 575.98px)").matches;
  const isDebugPage = () => /_debug\.html$/i.test(window.location.pathname || "");
  let adapting = false;

  const norm = (value) => (value || "").replace(/\s+/g, " ").trim();

  const findHeaders = (table) => {
    const headCells = table.querySelectorAll("thead tr:first-child th");
    if (headCells.length) return Array.from(headCells).map((cell) => norm(cell.textContent));
    const firstRow = table.querySelector("tr");
    if (!firstRow) return [];
    return Array.from(firstRow.cells || []).map((cell) => norm(cell.textContent));
  };

  const findRows = (table) => {
    const bodyRows = table.querySelectorAll("tbody tr");
    if (bodyRows.length) return Array.from(bodyRows);
    const rows = Array.from(table.querySelectorAll("tr"));
    return rows.length > 1 ? rows.slice(1) : rows;
  };

  const tableNeedsAlt = (table, headers) => {
    const viewport = window.innerWidth;
    const colCount = headers.length || (table.rows?.[0]?.cells?.length ?? 0);
    if (isDebugPage() && colCount >= 3) return true;
    if (colCount >= 5) return true;
    return table.scrollWidth > viewport + 24;
  };

  const createCard = (headers, row, index, maxFields = 8) => {
    const cells = Array.from(row.cells || []);
    if (!cells.length) return null;

    const card = document.createElement("div");
    card.className = "mobile-table-card";

    const titleText = norm(cells[0]?.textContent) || `Linha ${index + 1}`;
    const title = document.createElement("div");
    title.className = "mobile-table-card-title";
    title.textContent = titleText;
    card.appendChild(title);

    const maxIdx = Math.min(cells.length, maxFields + 1);
    for (let i = 1; i < maxIdx; i += 1) {
      const value = norm(cells[i]?.textContent);
      if (!value) continue;

      const rowWrap = document.createElement("div");
      rowWrap.className = "mobile-table-row";

      const key = document.createElement("div");
      key.className = "mobile-table-key";
      key.textContent = headers[i] || `Coluna ${i + 1}`;

      const val = document.createElement("div");
      val.className = "mobile-table-value";
      val.textContent = value;

      rowWrap.appendChild(key);
      rowWrap.appendChild(val);
      card.appendChild(rowWrap);
    }

    if (cells.length > maxFields + 1) {
      const more = document.createElement("div");
      more.className = "mobile-table-key";
      more.textContent = `+${cells.length - (maxFields + 1)} coluna(s) ocultas nesta visualização`;
      card.appendChild(more);
    }

    return card;
  };

  const markDone = () => {
    window.__mobileAdaptDone = true;
    document.documentElement.dataset.mobileAdaptDone = "1";
    window.dispatchEvent(new Event("mobile-adapt:done"));
  };

  const applyMobileTableAlternatives = () => {
    if (adapting || !isMobile()) return;
    adapting = true;
    document.documentElement.dataset.mobileAdaptDone = "0";
    try {
      document.querySelectorAll("table").forEach((table) => {
        if (table.dataset.mobileAltApplied === "1") return;
        if (table.dataset.mobileAlt === "off") return;
        if (table.classList.contains("cross-table")) return;
        if (table.closest(".mobile-alt-disabled")) return;

        const headers = findHeaders(table);
        if (!headers.length) return;
        if (!tableNeedsAlt(table, headers)) return;

        const rows = findRows(table);
        if (!rows.length) return;

        const debugMode = isDebugPage();
        const maxRows = debugMode
          ? Math.min(rows.length, 8)
          : rows.length > 60
            ? 12
            : rows.length > 30
              ? 16
              : rows.length;
        const visibleRows = rows.slice(0, maxRows);
        const maxFields = debugMode ? 6 : 8;

        const alt = document.createElement("div");
        alt.className = "mobile-table-alt";

        let target = alt;
        if (debugMode) {
          const details = document.createElement("details");
          details.className = "mobile-table-details";
          const summary = document.createElement("summary");
          summary.textContent = `Resumo mobile (${maxRows}/${rows.length} linhas)`;
          const body = document.createElement("div");
          body.className = "mobile-table-details-body";
          details.appendChild(summary);
          details.appendChild(body);
          alt.appendChild(details);
          target = body;
        }

        const note = document.createElement("div");
        note.className = "mobile-table-alt-note";
        note.textContent = "Visualização mobile compacta desta tabela.";
        target.appendChild(note);

        visibleRows.forEach((row, idx) => {
          const card = createCard(headers, row, idx, maxFields);
          if (card) target.appendChild(card);
        });

        if (rows.length > maxRows) {
          const trunc = document.createElement("div");
          trunc.className = "mobile-table-alt-note";
          trunc.textContent = `Mostrando ${maxRows} de ${rows.length} linhas.`;
          target.appendChild(trunc);
        }

        const reveal = document.createElement("div");
        reveal.className = "mobile-table-reveal";
        const btn = document.createElement("button");
        btn.type = "button";
        btn.textContent = "Ver tabela original";
        btn.addEventListener("click", () => {
          table.classList.remove("mobile-alt-source-hidden");
          alt.remove();
        });
        reveal.appendChild(btn);
        target.appendChild(reveal);

        table.dataset.mobileAltApplied = "1";
        table.classList.add("mobile-alt-source-hidden");
        table.insertAdjacentElement("afterend", alt);
      });
    } finally {
      adapting = false;
      markDone();
    }
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", applyMobileTableAlternatives, { once: true });
  } else {
    applyMobileTableAlternatives();
  }

  window.addEventListener(
    "resize",
    () => window.requestAnimationFrame(applyMobileTableAlternatives),
    { passive: true },
  );
})();
