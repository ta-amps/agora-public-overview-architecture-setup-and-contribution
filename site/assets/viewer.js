// Deck viewer: one slide at a time, scaled to fit, with keys, swipes, an outline,
// speaker notes and full screen. Without this script every slide is listed in order.
// The v4 viewer, shared by every current deck. Changes from v4: each slide's link uses its name
// (#slide-3 still works), the full-screen button and the announced words come from the page, which
// renders them from the site's text noun, and keys typed inside an element marked data-own-keys,
// such as the agent banner, stay with that element.
// October 30: the letter keys N and O act only while focus is on a slide or a deck control, and a
// checkbox in the help line turns them off (WCAG 2.1.4). On a screen with a mouse or trackpad, in a
// window wide enough to show a half-size slide at 100% zoom, a slide never shows below half its size,
// so browser zoom keeps enlarging it (WCAG 1.4.4); a slide wider than the window scrolls sideways
// inside its stage, and the arrow keys scroll it before they change slides. "Larger slides" shows
// every slide at its full 1920 by 1080 size, which browser zoom then enlarges in step.
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
  var largeButton = document.querySelector("[data-large-toggle]");
  var keysBox = document.querySelector("[data-keys-toggle]");
  var outline = document.getElementById("deck-outline");
  var outlineLinks = Array.prototype.slice.call(document.querySelectorAll("[data-goto]"));
  var baseTitle = document.title;
  var current = 0;

  var fullButton = document.querySelector("[data-full-toggle]");
  var fullLabel = fullButton ? fullButton.textContent : "";
  var canFull = !!(fullButton && document.fullscreenEnabled && stage.requestFullscreen);

  // The smallest scale on a screen with a fine pointer: half the slide's 1920 by 1080 size. Browser zoom
  // narrows the window in CSS pixels, so without this floor a refitted slide would shrink as fast as the
  // zoom enlarges it. The floor needs a window at least 1280 device pixels wide, which fits a half-size
  // slide without zoom, so a narrow or tiled window still fits its slide. Touch screens keep fitting the
  // width, and pinch zoom enlarges them.
  var MIN_SCALE = 0.5;
  var FLOOR_DEVICE_WIDTH = 1280;
  var finePointer = window.matchMedia ? window.matchMedia("(pointer: fine)") : null;

  function floorApplies() {
    return !!(finePointer && finePointer.matches) &&
      window.innerWidth * (window.devicePixelRatio || 1) >= FLOOR_DEVICE_WIDTH;
  }
  var large = false;
  var letterKeys = true;

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
    if (!full) {
      if (large) scale = Math.max(scale, 1);
      else if (floorApplies()) scale = Math.max(scale, MIN_SCALE);
    }
    stage.style.setProperty("--slide-scale", String(Math.max(scale, 0.1)));
    stage.classList.toggle("is-wide", stage.scrollWidth > stage.clientWidth + 1);
  }

  // A slide wider than its stage scrolls sideways first: true when the stage scrolled.
  function pan(direction) {
    var room = stage.scrollWidth - stage.clientWidth;
    if (room <= 1) return false;
    var x = stage.scrollLeft;
    if ((direction > 0 && x >= room - 1) || (direction < 0 && x <= 1)) return false;
    stage.scrollLeft = x + direction * Math.max(stage.clientWidth * 0.8, 40);
    return true;
  }

  function show(index, options) {
    options = options || {};
    var before = current;
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
    if (current !== before) stage.scrollLeft = 0;
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

  function setLarge(on, remember) {
    large = on;
    if (largeButton) largeButton.setAttribute("aria-pressed", on ? "true" : "false");
    if (remember) write("ta-amps-deck-large", on ? "1" : "0");
    fit();
  }

  function setLetterKeys(on, remember) {
    letterKeys = on;
    if (keysBox) keysBox.checked = on;
    if (remember) write("ta-amps-deck-letter-keys", on ? "1" : "0");
  }

  // Focus on a slide, a deck button, the outline or the help line: where the letter keys may act.
  function inDeck(target) {
    return !!(target && target.closest && target.closest("[data-stage], [data-controls], .deck-tools, #deck-outline, [data-help]"));
  }

  // Reveal the scripted controls only now that they work.
  [controls, help, notesButton, outlineButton, largeButton, canFull ? fullButton : null].forEach(function (el) { if (el) el.hidden = false; });

  prev.addEventListener("click", function () { show(current - 1); });
  next.addEventListener("click", function () { show(current + 1); });
  notesButton.addEventListener("click", function () { setNotes(!deck.classList.contains("show-notes"), true); });
  outlineButton.addEventListener("click", function () { setOutline(!outline.classList.contains("is-open")); });
  if (largeButton) largeButton.addEventListener("click", function () { setLarge(!large, true); });
  if (keysBox) keysBox.addEventListener("change", function () { setLetterKeys(keysBox.checked, true); });
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
    var letters = letterKeys && inDeck(target);
    switch (event.key) {
      case "ArrowRight":
        event.preventDefault(); if (!pan(1)) show(current + 1); break;
      case "PageDown":
        event.preventDefault(); show(current + 1); break;
      case "ArrowLeft":
        event.preventDefault(); if (!pan(-1)) show(current - 1); break;
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
        if (letters) setNotes(!deck.classList.contains("show-notes"), true);
        break;
      case "o":
      case "O":
        if (letters) setOutline(!outline.classList.contains("is-open"));
        break;
      case "Escape":
        if (outline.classList.contains("is-open")) { setOutline(false); outlineButton.focus(); }
        break;
      default:
        break;
    }
  });

  // Horizontal swipes change slides; vertical movement still scrolls the page. A slide wider than its
  // stage is panned by touch instead, and the Previous and Next buttons change slides.
  var startX = null;
  var startY = null;
  stage.addEventListener("pointerdown", function (event) {
    if (event.pointerType === "mouse" || stage.classList.contains("is-wide")) return;
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
  if (finePointer && finePointer.addEventListener) finePointer.addEventListener("change", fit);
  document.addEventListener("fullscreenchange", function () {
    if (fullButton) fullButton.textContent = document.fullscreenElement ? fullButton.getAttribute("data-exit") : fullLabel;
    fit();
  });
  window.addEventListener("hashchange", function () { show(fromHash(), { hash: false }); });

  slides.forEach(function (slide) { slide.tabIndex = -1; });
  var stored = read("ta-amps-deck-notes");
  setLetterKeys(read("ta-amps-deck-letter-keys") !== "0", false);
  large = read("ta-amps-deck-large") === "1";
  if (largeButton) largeButton.setAttribute("aria-pressed", large ? "true" : "false");
  setNotes(stored === null ? window.matchMedia("(max-width: 44rem)").matches : stored === "1", false);
  show(fromHash(), { hash: false, announce: false });
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(fit);
})();
