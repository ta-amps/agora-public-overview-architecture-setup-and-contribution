// The replay of one recorded run, on the how-it-works page. Without this script the stage shows the run's end and
// the list below it shows every step. With it, the Replay button steps through the run at about the design board's
// pace: each part of the stage appears at its step, each task shows its state after that step, the list marks the
// current step, and a status line says which step it is. Under reduced motion the steps change in place, without
// moving or fading. It reads only the page; it makes no request and uses no framework.
(function () {
  "use strict";
  var stage = document.querySelector("[data-rr-stage]");
  var button = document.querySelector("[data-rr-replay]");
  var list = document.getElementById("run-steps");
  var status = document.querySelector("[data-rr-status]");
  if (!stage || !button || !list) return;

  var PACE = 1000; // milliseconds between steps; the board uses 900
  var steps = Array.prototype.slice.call(list.querySelectorAll("[data-rr-step]"));
  var parts = Array.prototype.slice.call(stage.querySelectorAll("[data-at]"));
  var badges = Array.prototype.slice.call(stage.querySelectorAll("[data-states]"));
  var total = steps.length;
  var timers = [];

  // Each badge's states, step by step, as the page wrote them: {"1": "ready", "3": "done"}.
  var tracks = badges.map(function (badge) {
    try {
      return JSON.parse(badge.getAttribute("data-states")) || {};
    } catch (error) {
      return {};
    }
  });

  function stateAt(track, step) {
    var best = null;
    var bestStep = -1;
    Object.keys(track).forEach(function (key) {
      var n = Number(key);
      if (n <= step && n > bestStep) {
        bestStep = n;
        best = track[key];
      }
    });
    return best;
  }

  function show(step) {
    parts.forEach(function (part) {
      part.classList.toggle("rr-off", Number(part.getAttribute("data-at")) > step);
    });
    badges.forEach(function (badge, i) {
      var state = stateAt(tracks[i], step);
      if (!state) return;
      badge.textContent = state;
      badge.setAttribute("data-state", state);
      if (badge.parentNode && badge.parentNode.classList.contains("rr-task")) {
        badge.parentNode.setAttribute("data-state", state);
      }
    });
    steps.forEach(function (item) {
      var n = Number(item.getAttribute("data-rr-step"));
      item.classList.toggle("rr-current", n === step);
      item.classList.toggle("rr-later", n > step);
      if (n === step) item.setAttribute("aria-current", "step");
      else item.removeAttribute("aria-current");
    });
    if (status && step > 0) {
      var title = steps[step - 1].querySelector(".rr-title");
      status.textContent = status.getAttribute("data-step-word") + " " + step + " " +
        status.getAttribute("data-of-word") + " " + total + ": " + (title ? title.textContent : "");
    }
  }

  function replay() {
    timers.forEach(clearTimeout);
    timers = [];
    show(0);
    for (var step = 1; step <= total; step += 1) {
      timers.push(setTimeout(show, step * PACE - PACE / 2, step));
    }
  }

  button.hidden = false;
  button.addEventListener("click", replay);
})();
