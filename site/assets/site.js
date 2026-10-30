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
  // A choice that matches the system setting is not stored, so the page follows the system again
  // from then on, in this tab and the next.
  button.addEventListener("click", function () {
    var next = current() === "dark" ? "light" : "dark";
    var system = media && media.matches ? "dark" : "light";
    try {
      if (next === system) localStorage.removeItem("ta-amps-mode");
      else localStorage.setItem("ta-amps-mode", next);
    } catch (error) { /* storage can be unavailable */ }
    if (next === system) delete root.dataset.mode;
    else root.dataset.mode = next;
    render();
  });
  if (media && media.addEventListener) media.addEventListener("change", render);
})();

// Show and hide. A button with data-toggle="ID" shows or hides the element with that id, and swaps its
// label between data-closed and data-open. Without this script the button stays hidden, and an element
// marked data-no-script, such as a link to the same text, stays in its place.
(function () {
  Array.prototype.forEach.call(document.querySelectorAll("[data-no-script]"), function (el) { el.hidden = true; });

  function setOpen(button, panel, open) {
    panel.hidden = !open;
    button.setAttribute("aria-expanded", open ? "true" : "false");
    var label = button.querySelector("span");
    var words = button.getAttribute(open ? "data-open" : "data-closed");
    if (label && words) label.textContent = words;
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-toggle]"), function (button) {
    var panel = document.getElementById(button.getAttribute("data-toggle"));
    if (!panel) return;
    button.hidden = false;
    button.addEventListener("click", function () { setOpen(button, panel, panel.hidden); });
    panel.addEventListener("keydown", function (event) {
      if (event.key === "Escape") { setOpen(button, panel, false); button.focus(); }
    });
    button.taAmpsOpen = function () { setOpen(button, panel, true); };
  });
})();

// Copy buttons. A button with data-copy="ID" copies the text of the element with that id, then reads
// "Copied" for a moment. If the browser blocks the clipboard, the text is shown and selected instead,
// so it can be copied from the keyboard. A status element with the id "ID-status" announces either one.
(function () {
  function select(target) {
    var range = document.createRange();
    range.selectNodeContents(target);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    try { target.focus({ preventScroll: false }); } catch (error) { target.focus(); }
  }

  function legacyCopy(target) {
    select(target);
    try { return document.execCommand("copy"); } catch (error) { return false; }
  }

  Array.prototype.forEach.call(document.querySelectorAll("[data-copy]"), function (button) {
    var id = button.getAttribute("data-copy");
    var target = document.getElementById(id);
    var status = document.getElementById(id + "-status");
    if (!target) return;
    var label = button.querySelector("span") || button;
    var idle = label.textContent;
    var timer = null;
    button.hidden = false;

    function settle(state) {
      button.setAttribute("data-state", state);
      label.textContent = button.getAttribute(state === "copied" ? "data-copied" : "data-selected") || idle;
      if (status) {
        status.textContent = button.getAttribute(state === "copied" ? "data-status-copied" : "data-status-selected") ||
          label.textContent;
      }
      clearTimeout(timer);
      timer = setTimeout(function () {
        button.removeAttribute("data-state");
        label.textContent = idle;
      }, 2400);
    }

    function fallback() {
      var reveal = button.getAttribute("data-reveal");
      var toggle = reveal && document.querySelector('[data-toggle="' + reveal + '"]');
      if (toggle && toggle.taAmpsOpen) toggle.taAmpsOpen();
      if (legacyCopy(target)) settle("copied");
      else { select(target); settle("selected"); }
    }

    button.addEventListener("click", function () {
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(target.textContent).then(function () { settle("copied"); }, fallback);
      } else {
        fallback();
      }
    });
  });
})();

// Deck thumbnails: each card shows its deck's cover slide, scaled from 1920 pixels wide to the card.
(function () {
  var thumbs = Array.prototype.slice.call(document.querySelectorAll("[data-thumb]"));
  if (!thumbs.length) return;
  function fit(thumb) { thumb.style.setProperty("--thumb-scale", String(thumb.clientWidth / 1920)); }
  thumbs.forEach(fit);
  if (window.ResizeObserver) {
    var observer = new ResizeObserver(function (entries) { entries.forEach(function (entry) { fit(entry.target); }); });
    thumbs.forEach(function (thumb) { observer.observe(thumb); });
  } else {
    window.addEventListener("resize", function () { thumbs.forEach(fit); });
  }
})();

// Captions start on for a video marked data-captions-default, as its track's default flag asks.
(function () {
  Array.prototype.forEach.call(document.querySelectorAll("video[data-captions-default]"), function (video) {
    var tracks = video.textTracks;
    for (var i = 0; tracks && i < tracks.length; i++) {
      if (tracks[i].kind === "captions" || tracks[i].kind === "subtitles") { tracks[i].mode = "showing"; break; }
    }
  });
})();

// The film's cuts: one video element, and a button per cut that swaps its source, captions, poster and label.
// The address keeps the choice (?cut=short), so a cut can be linked and survives a reload. Captions stay
// as the viewer left them: on by default, and off after switching cuts only if they were turned off.
(function () {
  var group = document.querySelector("[data-film-cuts]");
  var video = document.querySelector(".film-video");
  if (!group || !video) return;
  var label = document.getElementById("film-label");
  var buttons = group.querySelectorAll("[data-cut]");
  var captionsOn = true;
  function captionTrack() {
    var tracks = video.textTracks;
    for (var i = 0; tracks && i < tracks.length; i++) {
      if (tracks[i].kind === "captions" || tracks[i].kind === "subtitles") return tracks[i];
    }
    return null;
  }
  function showCaptions() {
    var track = captionTrack();
    if (track) track.mode = captionsOn ? "showing" : "hidden";
  }
  function remember(cut, first) {
    if (!window.history || !history.replaceState || !window.URL) return;
    var url = new URL(location.href);
    if (cut === first) url.searchParams.delete("cut");
    else url.searchParams.set("cut", cut);
    if (url.href !== location.href) history.replaceState(history.state, "", url.href);
  }
  Array.prototype.forEach.call(buttons, function (button) {
    button.addEventListener("click", function () {
      if (button.getAttribute("aria-pressed") === "true") return;
      var shown = captionTrack();
      captionsOn = !shown || shown.mode === "showing";
      Array.prototype.forEach.call(buttons, function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      remember(button.getAttribute("data-cut"), buttons[0].getAttribute("data-cut"));
      video.pause();
      var source = video.querySelector("source");
      source.src = button.getAttribute("data-src");
      source.type = button.getAttribute("data-type");
      var old = video.querySelector("track");
      var track = document.createElement("track");
      ["kind", "srclang", "label"].forEach(function (name) { track.setAttribute(name, old.getAttribute(name)); });
      track.src = button.getAttribute("data-captions");
      track.default = true;
      video.replaceChild(track, old);
      video.poster = button.getAttribute("data-poster");
      video.setAttribute("aria-label", button.getAttribute("data-title"));
      var download = video.querySelector("a");
      if (download) download.href = button.getAttribute("data-src");
      if (label) label.textContent = button.getAttribute("data-label");
      video.load();
      track.addEventListener("load", showCaptions);
      showCaptions();
    });
  });
  group.hidden = false;
  var asked = window.URLSearchParams ? new URLSearchParams(location.search).get("cut") : null;
  Array.prototype.forEach.call(buttons, function (button) {
    if (asked && button.getAttribute("data-cut") === asked) button.click();
  });
})();
