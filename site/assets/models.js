// Models used (board ModelsUsed): choosing a step of the request track says what it runs on, in a polite live
// region, and lifts the model cards that step uses. Without this script every step stays readable and the
// default step's note shows. No storage, no network.
(function () {
  var buttons = Array.prototype.slice.call(document.querySelectorAll(".mu-step"));
  var note = document.getElementById("mu-step-note");
  if (!buttons.length || !note) return;
  function choose(button) {
    buttons.forEach(function (b) { b.setAttribute("aria-pressed", b === button ? "true" : "false"); });
    note.textContent = button.getAttribute("data-note") || "";
    var lift = (button.getAttribute("data-cards") || "").split(" ").filter(Boolean);
    Array.prototype.forEach.call(document.querySelectorAll(".mu-card[id]"), function (card) {
      card.setAttribute("data-lifted", lift.indexOf(card.id) >= 0 ? "true" : "false");
    });
  }
  buttons.forEach(function (b) { b.addEventListener("click", function () { choose(b); }); });
})();
