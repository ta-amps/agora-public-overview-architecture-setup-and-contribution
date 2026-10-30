// Deck viewer: one slide at a time, scaled to fit, with keys, swipes, an outline,
// speaker notes and full screen. Without this script every slide is listed in order.
// The v4 viewer, shared by every current deck. Changes from v4: each slide's link uses its name
// (#slide-3 still works), the full-screen button and the announced words come from the page, which
// renders them from the site's text noun, and keys typed inside an element marked data-own-keys,
// such as the agent banner, stay with that element.
(function () {
  var deck = document.querySelector(".deck");
  var stage = document.querySelector("[data-stage]");
  if (!deck || !stage) return;
  var slides = Array.prototype.slice.call(stage.querySelectorAll(".slide"));
  if (!slides.length) return;

  var controls = document.querySelector("[data-controls]");
  var help = document.querySelector("[data-help]");
  var prev = document.querySelector("[data-prev]");
  var next = document.querySelector("[data-next]");
  var counter = document.querySelector("[data-current]");
  var announce = document.querySelector("[data-announce]");
  var notesButton = document.querySelector("[data-notes-toggle]");
  var outlineButton = document.querySelector("[data-outline-toggle]");
  var outline = document.getElementById("deck-outline");
  var outlineLinks = Array.prototype.slice.call(document.querySelectorAll("[data-goto]"));
  var baseTitle = document.title;
  var current = 0;

  var fullButton = document.querySelector("[data-full-toggle]");
  var fullLabel = fullButton ? fullButton.textContent : "";
  var canFull = !!(fullButton && document.fullscreenEnabled && stage.requestFullscreen);

  function read(key) {
    try { return localStorage.getItem(key); } catch (error) { return null; }
  }

  function write(key, value) {
    try { localStorage.setItem(key, value); } catch (error) { /* storage can be unavailable */ }
  }

  function titleOf(slide) {
    var label = slide.getAttribute("aria-label") || "";
    return label.replace(/^\d+ of \d+: /, "");
  }

  function fit() {
    var slide = slides[current];
    var full = document.fullscreenElement === stage;
    var style = window.getComputedStyle(slide);
    var padding = full ? 0 : parseFloat(style.paddingLeft) + parseFloat(style.paddingRight);
    var width = (full ? stage.clientWidth : slide.clientWidth) - padding;
    var scale = width / 1920;
    var height;
    if (full) {
      height = stage.clientHeight;
    } else {
      var top = stage.getBoundingClientRect().top + window.scrollY;
      var below = controls ? controls.offsetHeight : 0;
      height = window.innerHeight - Math.min(top, window.innerHeight * 0.35) - below - 32;
    }
    if (full || height >= 300) scale = Math.min(scale, height / 1080);
    stage.style.setProperty("--slide-scale", String(Math.max(scale, 0.1)));
  }

  function show(index, options) {
    options = options || {};
    current = Math.max(0, Math.min(slides.length - 1, index));
    slides.forEach(function (slide, i) {
      var on = i === current;
      slide.classList.toggle("is-current", on);
      slide.setAttribute("aria-hidden", on ? "false" : "true");
    });
    outlineLinks.forEach(function (link) {
      if (Number(link.getAttribute("data-goto")) === current) link.setAttribute("aria-current", "true");
      else link.removeAttribute("aria-current");
    });
    counter.textContent = String(current + 1);
    prev.disabled = current === 0;
    next.disabled = current === slides.length - 1;
    var title = titleOf(slides[current]);
    document.title = (current + 1) + "/" + slides.length + " " + title + " | " + baseTitle;
    if (options.announce !== false && announce) {
      announce.textContent = (announce.getAttribute("data-prefix") || "") + " " + slides[current].getAttribute("aria-label");
    }
    if (options.hash !== false) history.replaceState(null, "", "#" + (slides[current].getAttribute("data-name") || "slide-" + (current + 1)));
    fit();
  }

  function fromHash() {
    var match = location.hash.match(/^#slide-(\d+)$/);
    if (match) return Number(match[1]) - 1;
    var name = decodeURIComponent(location.hash.slice(1));
    for (var i = 0; i < slides.length; i++) {
      if (name && slides[i].getAttribute("data-name") === name) return i;
    }
    return 0;
  }

  function setNotes(on, remember) {
    deck.classList.toggle("show-notes", on);
    notesButton.setAttribute("aria-pressed", on ? "true" : "false");
    if (remember) write("ta-amps-deck-notes", on ? "1" : "0");
    fit();
  }

  function setOutline(open) {
    outline.classList.toggle("is-open", open);
    outlineButton.setAttribute("aria-expanded", open ? "true" : "false");
  }

  // Reveal the scripted controls only now that they work.
  [controls, help, notesButton, outlineButton, canFull ? fullButton : null].forEach(function (el) { if (el) el.hidden = false; });

  prev.addEventListener("click", function () { show(current - 1); });
  next.addEventListener("click", function () { show(current + 1); });
  notesButton.addEventListener("click", function () { setNotes(!deck.classList.contains("show-notes"), true); });
  outlineButton.addEventListener("click", function () { setOutline(!outline.classList.contains("is-open")); });
  if (canFull) {
    fullButton.addEventListener("click", function () {
      if (document.fullscreenElement) document.exitFullscreen();
      else stage.requestFullscreen().catch(function () { /* the browser refused */ });
    });
  }

  outlineLinks.forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      show(Number(link.getAttribute("data-goto")));
      setOutline(false);
      slides[current].focus({ preventScroll: true });
      stage.scrollIntoView({ block: "nearest" });
    });
  });

  document.addEventListener("keydown", function (event) {
    if (event.altKey || event.ctrlKey || event.metaKey) return;
    var target = event.target;
    var tag = target && target.tagName;
    if (/^(INPUT|TEXTAREA|SELECT)$/.test(tag) || (target && target.isContentEditable)) return;
    if (target && target.closest && target.closest("[data-own-keys]")) return;
    var onControl = /^(BUTTON|A|SUMMARY)$/.test(tag);
    switch (event.key) {
      case "ArrowRight":
      case "PageDown":
        event.preventDefault(); show(current + 1); break;
      case "ArrowLeft":
      case "PageUp":
        event.preventDefault(); show(current - 1); break;
      case " ":
        if (onControl) return;
        event.preventDefault(); show(event.shiftKey ? current - 1 : current + 1); break;
      case "Home":
        event.preventDefault(); show(0); break;
      case "End":
        event.preventDefault(); show(slides.length - 1); break;
      case "n":
      case "N":
        setNotes(!deck.classList.contains("show-notes"), true); break;
      case "o":
      case "O":
        setOutline(!outline.classList.contains("is-open")); break;
      case "Escape":
        if (outline.classList.contains("is-open")) { setOutline(false); outlineButton.focus(); }
        break;
      default:
        break;
    }
  });

  // Horizontal swipes change slides; vertical movement still scrolls the page.
  var startX = null;
  var startY = null;
  stage.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "mouse") return;
    startX = event.clientX;
    startY = event.clientY;
  });
  stage.addEventListener("pointerup", function (event) {
    if (startX === null) return;
    var dx = event.clientX - startX;
    var dy = event.clientY - startY;
    startX = null;
    if (Math.abs(dx) > 40 && Math.abs(dx) > Math.abs(dy) * 1.5) show(current + (dx < 0 ? 1 : -1));
  });
  stage.addEventListener("pointercancel", function () { startX = null; });

  window.addEventListener("resize", fit);
  document.addEventListener("fullscreenchange", function () {
    if (fullButton) fullButton.textContent = document.fullscreenElement ? fullButton.getAttribute("data-exit") : fullLabel;
    fit();
  });
  window.addEventListener("hashchange", function () { show(fromHash(), { hash: false }); });

  slides.forEach(function (slide) { slide.tabIndex = -1; });
  var stored = read("ta-amps-deck-notes");
  setNotes(stored === null ? window.matchMedia("(max-width: 44rem)").matches : stored === "1", false);
  show(fromHash(), { hash: false, announce: false });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
})();
