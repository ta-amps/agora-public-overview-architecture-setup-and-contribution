/*
 * <ta-judge-tour>: the 45-second tour for judges, one strip under a site's header, shown only when the address has
 * ?tour=judge (or the tour was opened earlier in this tab). It follows the JudgeTour board: the label, five numbered
 * steps (done ones show a check, the current one is dark and aria-current="step"), a link to the next page and a
 * close button. Every word and address comes from the judge-tour noun, embedded as
 *   <ta-judge-tour><script type="application/json">{ ...the noun... }</script></ta-judge-tour>
 * or read from a `src` address, as the agent banner does. Eranos and Agora include the same file. No network calls of
 * its own unless `src` asks for one; the only storage is a per-tab flag so the tour survives a click within a site.
 */
(() => {
  if (typeof customElements === "undefined" || customElements.get("ta-judge-tour")) return;
  const KEY = "ta-judge-tour";
  const CSS = `
:host { display: block; font-family: "IBM Plex Sans", "Segoe UI", system-ui, sans-serif;
  --jt-bg: var(--judge-tour-bg, #FFFDF8); --jt-ink: var(--judge-tour-ink, #11161F); --jt-muted: var(--judge-tour-muted, #5E6472);
  --jt-line: var(--judge-tour-line, #E2DCCF); --jt-dot: var(--judge-tour-dot, #EDE8DC); --jt-link: var(--judge-tour-link, #24519B);
  --jt-focus: var(--judge-tour-focus, #2A5DB0); }
:host([hidden]) { display: none; }
* { box-sizing: border-box; }
nav { min-height: 52px; padding: 6px 24px; display: flex; align-items: center; gap: 8px 14px; flex-wrap: wrap;
  background: var(--jt-bg); color: var(--jt-ink); border-bottom: 1px solid var(--jt-line); }
b { font-size: 15px; white-space: nowrap; }
ol { list-style: none; margin: 0; padding: 0; display: flex; gap: 6px; flex: 1 1 auto; min-width: 0; flex-wrap: wrap; }
li { display: flex; align-items: center; gap: 6px; padding: 5px 11px 5px 5px; border-radius: 999px; font-size: 14px; font-weight: 600;
  white-space: nowrap; color: var(--jt-muted); }
li[data-done] { color: var(--jt-ink); }
li[aria-current="step"] { background: var(--jt-ink); color: var(--jt-bg); }
.dot { width: 22px; height: 22px; border-radius: 11px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px;
  background: var(--jt-dot); color: var(--jt-ink); }
li[data-done] .dot { background: var(--jt-ink); color: var(--jt-bg); }
li[aria-current="step"] .dot { background: var(--jt-bg); color: var(--jt-ink); }
a { font-size: 15px; font-weight: 600; color: var(--jt-link); white-space: nowrap; text-underline-offset: 0.18em; }
button { font: inherit; font-size: 18px; line-height: 1; width: 36px; height: 36px; border-radius: 10px; border: 1.5px solid var(--jt-muted);
  background: var(--jt-bg); color: var(--jt-ink); cursor: pointer; flex: none; }
a:focus-visible, button:focus-visible { outline: 3px solid var(--jt-focus); outline-offset: 2px; }
@media (max-width: 719.98px) { nav { padding: 8px 16px; } li .label { display: none; } li[aria-current="step"] .label { display: inline; } }
`;

  function el(tag, props, children) {
    const node = document.createElement(tag);
    for (const [name, value] of Object.entries(props || {})) {
      if (value === undefined || value === null || value === false) continue;
      if (name === "text") node.textContent = String(value);
      else if (name.startsWith("on")) node.addEventListener(name.slice(2), value);
      else node.setAttribute(name, value === true ? "" : String(value));
    }
    for (const child of children || []) if (child) node.append(child);
    return node;
  }

  function safeHref(value) {
    try {
      const url = new URL(value, window.location.href);
      return url.protocol === "https:" || url.protocol === "http:" ? url.href : "#";
    } catch (e) {
      return "#";
    }
  }

  function stepFor(noun, loc, host) {
    // The most specific step whose host and path match this page; a step with a hash wins when the hash matches. The
    // host is the site the page belongs to (data-host on the element), so a local preview counts as that site.
    let best = -1, bestScore = -1;
    noun.steps.forEach((step, i) => {
      if (step.host && step.host !== host) return;
      const path = step.path || "/";
      const ok = path === "/" ? true : (path.endsWith("/") ? loc.pathname.startsWith(path) : loc.pathname === path || loc.pathname === `${path}/`);
      if (!ok) return;
      let score = path.length;
      if (step.hash) { if (loc.hash !== step.hash) return; score += 1000; }
      if (score > bestScore) { best = i; bestScore = score; }
    });
    return best;
  }

  function active(noun) {
    const params = new URLSearchParams(window.location.search);
    if (params.get(noun.param) === noun.value) {
      try { sessionStorage.setItem(KEY, "1"); } catch (e) { /* the tour still shows on this page */ }
      return true;
    }
    try { return sessionStorage.getItem(KEY) === "1"; } catch (e) { return false; }
  }

  class JudgeTour extends HTMLElement {
    constructor() {
      super();
      this.root = this.attachShadow({ mode: "open" });
      this.hidden = true;
      this.onHash = () => this.noun && this.render(this.noun);
    }

    connectedCallback() {
      window.addEventListener("hashchange", this.onHash);
      if (this.started) return;
      this.started = true;
      const inline = this.querySelector('script[type="application/json"]');
      const load = inline ? Promise.resolve(JSON.parse(inline.textContent))
        : (this.getAttribute("src") ? fetch(this.getAttribute("src"), { credentials: "omit" }).then((r) => r.json()) : Promise.reject());
      load.then((noun) => { this.noun = noun; this.render(noun); }).catch(() => { this.hidden = true; });
    }

    disconnectedCallback() { window.removeEventListener("hashchange", this.onHash); }

    close() {
      try { sessionStorage.removeItem(KEY); } catch (e) { /* nothing stored */ }
      const url = new URL(window.location.href);
      url.searchParams.delete(this.noun.param);
      history.replaceState(history.state, "", url.pathname + (url.search || "") + url.hash);
      this.hidden = true;
      this.dataset.active = "false";
    }

    render(noun) {
      if (!active(noun)) { this.hidden = true; return; }
      const current = stepFor(noun, window.location, this.getAttribute("data-host") || window.location.host);
      if (current < 0) { this.hidden = true; return; }
      const steps = noun.steps.map((step, i) => el("li", {
        "aria-current": i === current ? "step" : null, "data-done": i < current ? true : null,
      }, [el("span", { class: "dot", "aria-hidden": "true", text: i < current ? "✓" : String(i + 1) }), el("span", { class: "label", text: step.label })]));
      const step = noun.steps[current];
      const nav = el("nav", { "aria-label": noun.label }, [
        el("b", { text: noun.label }),
        el("ol", {}, steps),
        el("a", { href: safeHref(step.next_href), text: step.next }),
        el("button", { type: "button", "aria-label": noun.close, text: "×", onclick: () => this.close() }),
      ]);
      if ("adoptedStyleSheets" in Document.prototype && "replaceSync" in CSSStyleSheet.prototype) {
        const sheet = new CSSStyleSheet();
        sheet.replaceSync(CSS);
        this.root.adoptedStyleSheets = [sheet];
        this.root.replaceChildren(nav);
      } else {
        this.root.replaceChildren(el("style", { text: CSS }), nav);
      }
      this.hidden = false;
      this.dataset.active = "true";
      this.dataset.step = String(current + 1);
    }
  }

  customElements.define("ta-judge-tour", JudgeTour);
})();
