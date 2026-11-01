/*
 * Client-side domain filter and verdict sorter for /scenarios/.
 * Purely offline over the rendered table rows: zero network calls, zero browser storage.
 */
(() => {
  const tbody = document.querySelector("[data-scenarios-rows]");
  if (!tbody) return;
  const allRows = Array.from(tbody.querySelectorAll("tr[data-domain-kind]"));
  const filterBtns = Array.from(document.querySelectorAll("[data-sc-filter]"));
  const tileBtns = Array.from(document.querySelectorAll("[data-sc-verdict]"));
  const statusEl = document.querySelector("[data-sc-status]");

  let filter = "all";
  let verdict = null;

  function render() {
    for (const btn of filterBtns) {
      btn.setAttribute("aria-pressed", btn.dataset.scFilter === filter ? "true" : "false");
    }
    for (const btn of tileBtns) {
      btn.setAttribute("aria-pressed", btn.dataset.scVerdict === verdict ? "true" : "false");
    }
    let visible = allRows.filter((row) => filter === "all" || row.dataset.domainKind === filter);
    if (verdict) {
      const attrName = `data-${verdict}`;
      visible = visible.slice().sort((a, b) => Number(b.getAttribute(attrName)) - Number(a.getAttribute(attrName)));
    }
    for (const row of allRows) {
      row.hidden = !visible.includes(row);
    }
    for (const row of visible) {
      tbody.appendChild(row);
    }
    if (statusEl) {
      const sortNote = verdict ? `, sorted by ${verdict}` : "";
      statusEl.textContent = `Showing ${visible.length} of ${allRows.length} kinds of work${sortNote}.`;
    }
  }

  for (const btn of filterBtns) {
    btn.addEventListener("click", () => {
      filter = btn.dataset.scFilter;
      render();
    });
  }
  for (const btn of tileBtns) {
    btn.addEventListener("click", () => {
      const key = btn.dataset.scVerdict;
      verdict = verdict === key ? null : key;
      render();
    });
  }
})();
