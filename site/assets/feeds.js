/*
 * Client-side category switcher and 'Which fits?' filter for /feeds/.
 * Purely offline over the embedded #agora-feeds-data noun: zero network calls, zero browser storage.
 */
(() => {
  const dataEl = document.getElementById("agora-feeds-data");
  if (!dataEl) return;
  let model;
  try {
    model = JSON.parse(dataEl.textContent);
  } catch (e) {
    return;
  }
  const catButtons = Array.from(document.querySelectorAll("[data-feed-cat]"));
  const optButtons = Array.from(document.querySelectorAll("[data-feed-q][data-feed-val]"));
  const headingEl = document.getElementById("h-feed");
  const scheduleEl = document.querySelector("[data-feed-schedule]");
  const rankEl = document.querySelector("[data-feed-rank]");
  const metricTh = document.querySelector("[data-feed-metric]");
  const tbody = document.querySelector("[data-feed-rows]");
  const detailLink = document.querySelector("[data-feed-detail]");
  const fitNameEl = document.querySelector("[data-feed-fit-name]");
  const fitWhyEl = document.querySelector("[data-feed-fit-why]");
  const snippetEl = document.querySelector("[data-feed-snippet]");
  if (!tbody || !model.categories || !model.categories.length) return;

  const state = {
    cat: model.categories[0].key,
    data: "private",
    runs: "local",
  };

  function el(tag, attrs, children) {
    const node = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === null || v === undefined) continue;
      if (k === "text") node.textContent = String(v);
      else node.setAttribute(k, String(v));
    }
    for (const c of children || []) if (c) node.append(c);
    return node;
  }

  function render() {
    const cur = model.categories.find((c) => c.key === state.cat) || model.categories[0];
    for (const btn of catButtons) {
      btn.setAttribute("aria-pressed", btn.dataset.feedCat === cur.key ? "true" : "false");
    }
    for (const btn of optButtons) {
      const active = state[btn.dataset.feedQ] === btn.dataset.feedVal;
      btn.setAttribute("aria-pressed", active ? "true" : "false");
    }
    if (headingEl) headingEl.textContent = cur.name;
    if (scheduleEl) scheduleEl.textContent = `${cur.schedule} · ${cur.last_run} · receipt ${cur.receipt}`;
    if (rankEl) rankEl.textContent = cur.rank;
    if (metricTh) metricTh.textContent = cur.metric;
    if (detailLink) {
      detailLink.setAttribute("href", cur.detail_href);
      detailLink.textContent = cur.detail_label;
    }

    const forcedLocal = state.data !== "public" && state.runs === "cloud";
    const effectiveRuns = forcedLocal ? "local" : state.runs;
    const rows = cur.rows.filter((r) => {
      if (effectiveRuns === "either") return true;
      return r.runs === effectiveRuns || r.runs === "either";
    });
    const shownRows = rows.length ? rows : cur.rows;

    tbody.replaceChildren(
      ...shownRows.map((r, idx) => {
        const barFill = el("span", { class: "fd-bar-fill" });
        barFill.style.width = `${Math.max(8, Math.min(100, Number(r.bar_pct) || 50))}%`;
        return el("tr", {}, [
          el("td", { class: "fd-num", text: String(idx + 1) }),
          el("td", { class: "fd-tool" }, [el("a", { href: r.url, text: r.name })]),
          el("td", {}, [
            el("span", { class: "fd-signal-wrap" }, [
              el("span", { class: "fd-bar", "aria-hidden": "true" }, [barFill]),
              el("span", { class: "fd-signal", text: r.signal }),
            ]),
          ]),
          el("td", { class: "fd-mono", text: r.runs_label }),
          el("td", { class: "fd-mono", text: r.license }),
        ]);
      })
    );

    const best = shownRows[0];
    if (fitNameEl && best) {
      fitNameEl.textContent = `${best.name} (${best.runs_label}, ${best.license})`;
    }
    if (fitWhyEl) {
      fitWhyEl.textContent = forcedLocal ? model.forced_local_why : model.default_why;
    }
    if (snippetEl) {
      snippetEl.textContent = `which_fits({ feed: "${cur.key}", data: "${state.data}", runs: "${effectiveRuns}" })`;
    }
  }

  for (const btn of catButtons) {
    btn.addEventListener("click", () => {
      state.cat = btn.dataset.feedCat;
      render();
    });
  }
  for (const btn of optButtons) {
    btn.addEventListener("click", () => {
      state[btn.dataset.feedQ] = btn.dataset.feedVal;
      render();
    });
  }
  render();
})();
