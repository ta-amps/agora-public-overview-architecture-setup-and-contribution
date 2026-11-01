/*
 * Client-side live health probe for /status/.
 * Probes only endpoints in Agora's CSP connect-src ('self', tessera, herma, eranos)
 * with credentials omitted and honest fallback to the saved snapshot when offline.
 */
(() => {
  const banner = document.querySelector("[data-status-overall]");
  const titleEl = document.querySelector("[data-status-title]");
  const noteEl = document.querySelector("[data-status-note]");
  const recheckBtn = document.querySelector("[data-status-recheck]");
  const rows = Array.from(document.querySelectorAll("tr[data-probe-url]"));
  if (!banner || !rows.length) return;

  if (recheckBtn) recheckBtn.hidden = false;

  async function probeOne(row) {
    const url = row.getAttribute("data-probe-url");
    const badge = row.querySelector("[data-status-state]");
    const since = row.querySelector("[data-status-since]");
    if (!url || !badge) return null;
    const ctrl = typeof AbortController !== "undefined" ? new AbortController() : null;
    const timer = ctrl ? setTimeout(() => ctrl.abort(), 5000) : null;
    const t0 = performance.now();
    try {
      const res = await fetch(url, {
        method: "GET",
        credentials: "omit",
        cache: "no-store",
        signal: ctrl ? ctrl.signal : undefined,
      });
      if (timer) clearTimeout(timer);
      const ms = Math.round(performance.now() - t0);
      if (res.ok) {
        const slow = ms > 1500;
        badge.dataset.kind = slow ? "slow" : "ok";
        const icon = badge.querySelector("[data-status-icon]");
        const text = badge.querySelector("[data-status-label]");
        if (icon) icon.textContent = slow ? "!" : "✓";
        if (text) text.textContent = slow ? `Slow (${ms} ms)` : `Answering (${ms} ms)`;
        if (since) since.textContent = "Live check just now";
        return "ok";
      }
      badge.dataset.kind = "recorded";
      return "recorded";
    } catch (e) {
      if (timer) clearTimeout(timer);
      badge.dataset.kind = "recorded";
      const icon = badge.querySelector("[data-status-icon]");
      const text = badge.querySelector("[data-status-label]");
      if (icon) icon.textContent = "○";
      if (text && !text.textContent.includes("Saved")) {
        text.textContent = "Saved snapshot (browser offline)";
      }
      return "offline";
    }
  }

  async function runChecks() {
    if (recheckBtn) recheckBtn.disabled = true;
    if (noteEl && banner.dataset.checkingText) {
      noteEl.textContent = banner.dataset.checkingText;
    }
    const results = await Promise.all(rows.map(probeOne));
    const allOk = results.every((r) => r === "ok");
    if (allOk) {
      if (titleEl && banner.dataset.liveAllOk) titleEl.textContent = banner.dataset.liveAllOk;
      if (noteEl) noteEl.textContent = "All probed services answered live HTTP 200 from this browser.";
    } else {
      if (noteEl && banner.dataset.livePartial) noteEl.textContent = banner.dataset.livePartial;
    }
    if (recheckBtn) recheckBtn.disabled = false;
  }

  if (recheckBtn) {
    recheckBtn.addEventListener("click", () => { runChecks(); });
  }
  runChecks();
})();
