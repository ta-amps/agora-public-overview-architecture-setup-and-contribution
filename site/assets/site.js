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

// Copy buttons. A button with data-copy="ID" copies the text of the element with that id.
// Without this script, or without the clipboard API, the button stays hidden and the text can be selected.
(function () {
  if (!navigator.clipboard || !navigator.clipboard.writeText) return;
  Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (button) {
    var target = document.getElementById(button.getAttribute("data-copy"));
    var status = document.getElementById(button.getAttribute("data-copy") + "-status");
    if (!target) return;
    button.hidden = false;
    button.addEventListener("click", function () {
      navigator.clipboard.writeText(target.textContent).then(function () {
        if (status) status.textContent = "Copied.";
      }, function () {
        if (status) status.textContent = "Copying failed. Select the text and copy it instead.";
      });
    });
  });
})();
