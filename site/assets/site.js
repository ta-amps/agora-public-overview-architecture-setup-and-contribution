// Light and dark mode switch. Without this script the page follows the
// system setting, and the switch stays hidden.
(function () {
  var root = document.documentElement;
  var button = document.querySelector("[data-mode-toggle]");
  if (!button) return;
  var media = window.matchMedia ? window.matchMedia("(prefers-color-scheme: dark)") : null;

  function current() {
    if (root.dataset.mode === "dark" || root.dataset.mode === "light") return root.dataset.mode;
    return media && media.matches ? "dark" : "light";
  }

  function render() {
    button.setAttribute("aria-pressed", current() === "dark" ? "true" : "false");
  }

  button.hidden = false;
  render();
  button.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    root.dataset.mode = next;
    try { localStorage.setItem("ta-amps-mode", next); } catch (error) { /* storage can be unavailable */ }
    render();
  });
  if (media && media.addEventListener) media.addEventListener("change", render);
})();
