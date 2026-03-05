// Mobile-first adaptations for dense/wide tables.
// Converts wide tables to compact card views on phones while keeping
// the original table available on demand.

(() => {
  const isMobile = () => window.matchMedia("(max-width: 575.98px)").matches;
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
    if (colCount >= 5) return true;
    return table.scrollWidth > viewport + 24;
  };

  const createCard = (headers, row, index) => {
    const cells = Array.from(row.cells || []);
    if (!cells.length) return null;

    const card = document.createElement("div");
    card.className = "mobile-table-card";

    const titleText = norm(cells[0]?.textContent) || `Linha ${index + 1}`;
    const title = document.createElement("div");
    title.className = "mobile-table-card-title";
    title.textContent = titleText;
    card.appendChild(title);

    const maxFields = 8;
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

  const applyMobileTableAlternatives = () => {
    if (adapting || !isMobile()) return;
    adapting = true;
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

        const maxRows = rows.length > 40 ? 24 : rows.length;
        const visibleRows = rows.slice(0, maxRows);

        const alt = document.createElement("div");
        alt.className = "mobile-table-alt";

        const note = document.createElement("div");
        note.className = "mobile-table-alt-note";
        note.textContent = "Visualização mobile compacta desta tabela.";
        alt.appendChild(note);

        visibleRows.forEach((row, idx) => {
          const card = createCard(headers, row, idx);
          if (card) alt.appendChild(card);
        });

        if (rows.length > maxRows) {
          const trunc = document.createElement("div");
          trunc.className = "mobile-table-alt-note";
          trunc.textContent = `Mostrando ${maxRows} de ${rows.length} linhas.`;
          alt.appendChild(trunc);
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
        alt.appendChild(reveal);

        table.dataset.mobileAltApplied = "1";
        table.classList.add("mobile-alt-source-hidden");
        table.insertAdjacentElement("afterend", alt);
      });
    } finally {
      adapting = false;
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
