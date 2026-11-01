// Use cases (board UseCases): the filter shows all cases or one audience. The featured run belongs to nonprofits.
// Without this script every case shows and the filter stays hidden. No storage, no network.
(function () {
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".uc-filter-button"));
  if (!buttons.length) return;
  var items = Array.prototype.slice.call(document.querySelectorAll(".uc-page [data-audience]"));
  function show(key) {
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", b.getAttribute("data-filter") === key ? "true" : "false"); });
    items.forEach(function (el) { el.hidden = key !== "all" && el.getAttribute("data-audience") !== key; });
  }
  buttons.forEach(function (b) { b.addEventListener("click", function () { show(b.getAttribute("data-filter")); }); });
})();
