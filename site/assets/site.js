// Light only (owner, Nov 1): there is no mode switch. The page marks that scripts run, for the parts that need them.
document.documentElement.classList.add("js");

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

// The header's Menu button on narrow screens: it opens and closes the five links. Without this script the
// button stays hidden and the links wrap under the name instead.
(function () {
  var button = document.querySelector("[data-menu-toggle]");
  var nav = button && document.getElementById(button.getAttribute("aria-controls"));
  if (!nav) return;
  var label = button.querySelector("span");
  function setOpen(open) {
    nav.classList.toggle("is-open", open);
    var header = button.closest(".site-header");
    if (header) header.classList.toggle("menu-open", open);
    button.setAttribute("aria-expanded", open ? "true" : "false");
    if (label) label.textContent = button.getAttribute(open ? "data-open" : "data-closed");
  }
  button.hidden = false;
  button.addEventListener("click", function () { setOpen(!nav.classList.contains("is-open")); });
  nav.addEventListener("keydown", function (event) {
    if (event.key === "Escape" && nav.classList.contains("is-open")) { setOpen(false); button.focus(); }
  });
})();

// The not-found page names the address that was asked for, as text.
(function () {
  var slot = document.querySelector("[data-missing-path]");
  if (slot) slot.textContent = window.location.pathname;
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

// The film's cuts and widescreen bottom-border caption bar: one video element, a button per cut that swaps its
// source, captions, poster and label, and a custom rounded caption pill inside the bottom grayish-black letterbox
// band synchronized with textTracks (kept in mode="hidden" inline so native browser cue boxes never appear).
(function () {
  var video = document.querySelector(".film-video");
  if (!video) return;
  var stage = video.closest(".film-stage");
  var group = document.querySelector("[data-film-cuts]");
  var captionBar = document.querySelector("[data-film-caption-bar]");
  var captionPill = document.querySelector("[data-film-caption-pill]");
  var ccButton = document.querySelector("[data-film-cc]");
  var label = document.getElementById("film-label");
  var buttons = group ? group.querySelectorAll("[data-cut]") : [];
  var captionsOn = video.hasAttribute("data-captions-default");
  var applyingMode = false;
  var openSrc = video.getAttribute("data-open-src") || "";
  var cleanSrc = video.getAttribute("data-clean-src") || "";

  function captionTrack() {
    var tracks = video.textTracks;
    for (var i = 0; tracks && i < tracks.length; i++) {
      if (tracks[i].kind === "captions" || tracks[i].kind === "subtitles") return tracks[i];
    }
    return null;
  }

  function stripVttTags(raw) {
    return String(raw || "").replace(/<[^>]+>/g, "").trim();
  }

  function desiredTrackMode() {
    return captionsOn ? "hidden" : "disabled";
  }

  function enforceTrackMode() {
    var track = captionTrack();
    if (!track) return;
    var want = desiredTrackMode();
    if (track.mode !== want) {
      applyingMode = true;
      track.mode = want;
      applyingMode = false;
    }
  }

  function syncVideoSourceForCaptions() {
    if (!cleanSrc || !openSrc) return;
    var source = video.querySelector("source");
    if (!source) return;
    var wantSrc = captionsOn ? openSrc : cleanSrc;
    if (source.getAttribute("src") === wantSrc) return;
    var resumeTime = video.currentTime || 0;
    var wasPlaying = !video.paused && !video.ended;
    source.setAttribute("src", wantSrc);
    var download = video.querySelector("a");
    if (download) download.setAttribute("href", wantSrc);
    video.load();
    if (resumeTime > 0 || wasPlaying) {
      video.addEventListener("loadedmetadata", function restorePlayback() {
        video.removeEventListener("loadedmetadata", restorePlayback);
        if (resumeTime > 0) {
          try { video.currentTime = resumeTime; } catch (err) {}
        }
        if (wasPlaying) {
          var p = video.play();
          if (p && p.catch) p.catch(function () {});
        }
      });
    }
  }

  function syncCaptionPill() {
    enforceTrackMode();
    var track = captionTrack();
    if (ccButton) {
      ccButton.setAttribute("aria-pressed", captionsOn ? "true" : "false");
      ccButton.textContent = ccButton.getAttribute(captionsOn ? "data-label-on" : "data-label-off") ||
        (captionsOn ? "Captions · On" : "Captions · Off");
    }
    if (!captionBar || !captionPill) return;
    if (cleanSrc || video.hasAttribute("data-open-captions")) {
      captionBar.hidden = true;
      captionPill.textContent = "";
      return;
    }
    if (!captionsOn || !track || !track.activeCues || !track.activeCues.length) {
      captionBar.hidden = true;
      captionPill.textContent = "";
      return;
    }
    var lines = [];
    for (var i = 0; i < track.activeCues.length; i++) {
      var clean = stripVttTags(track.activeCues[i].text);
      if (clean) lines.push(clean);
    }
    if (!lines.length) {
      captionBar.hidden = true;
      captionPill.textContent = "";
      return;
    }
    captionPill.textContent = lines.join("\n");
    captionBar.hidden = false;
  }

  function attachTrackListeners() {
    var track = captionTrack();
    if (!track || track._taBound) return;
    track._taBound = true;
    track.addEventListener("cuechange", syncCaptionPill);
  }

  function showCaptions() {
    enforceTrackMode();
    attachTrackListeners();
    syncCaptionPill();
  }

  if (video.textTracks && video.textTracks.addEventListener) {
    video.textTracks.addEventListener("change", function () {
      if (applyingMode) return;
      var track = captionTrack();
      if (track && document.fullscreenElement !== video) {
        if (track.mode === "showing") captionsOn = true;
        else if (track.mode === "disabled") captionsOn = false;
      }
      showCaptions();
    });
  }
  function syncPausedAttr() {
    if (stage) stage.setAttribute("data-paused", video.paused ? "true" : "false");
  }
  video.addEventListener("play", syncPausedAttr);
  video.addEventListener("pause", syncPausedAttr);
  video.addEventListener("ended", syncPausedAttr);
  video.addEventListener("loadedmetadata", showCaptions);
  video.addEventListener("loadedmetadata", syncPausedAttr);
  video.addEventListener("timeupdate", syncCaptionPill);
  document.addEventListener("fullscreenchange", showCaptions);
  syncPausedAttr();
  showCaptions();

  if (ccButton) {
    ccButton.addEventListener("click", function () {
      captionsOn = !captionsOn;
      syncVideoSourceForCaptions();
      showCaptions();
    });
  }

  if (!group || !buttons.length) return;

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
      Array.prototype.forEach.call(buttons, function (other) {
        other.setAttribute("aria-pressed", other === button ? "true" : "false");
      });
      remember(button.getAttribute("data-cut"), buttons[0].getAttribute("data-cut"));
      video.pause();
      openSrc = button.getAttribute("data-src") || "";
      cleanSrc = button.getAttribute("data-clean-src") || "";
      var chosenSrc = (cleanSrc && !captionsOn) ? cleanSrc : openSrc;
      var source = video.querySelector("source");
      source.setAttribute("src", chosenSrc);
      source.type = button.getAttribute("data-type");
      var old = video.querySelector("track");
      var track = document.createElement("track");
      ["kind", "srclang", "label"].forEach(function (name) { track.setAttribute(name, old.getAttribute(name)); });
      track.src = button.getAttribute("data-captions");
      if (captionsOn) track.default = true;
      video.replaceChild(track, old);
      video.poster = button.getAttribute("data-poster");
      video.setAttribute("aria-label", button.getAttribute("data-title"));
      var download = video.querySelector("a");
      if (download) download.setAttribute("href", chosenSrc);
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

// Interactive Task, Task-Object & Meta Hackathon Ecosystem Explorer on the Library page.
// Reads the static #agora-explorer-data JSON block in the page; zero network traffic and zero browser storage.
(function () {
  var dataNode = document.getElementById("agora-explorer-data");
  var shell = document.getElementById("explorer");
  if (!dataNode || !shell) return;
  var data;
  try {
    data = JSON.parse(dataNode.textContent);
  } catch (err) {
    return;
  }
  var controls = shell.querySelector("[data-exp-controls]");
  var queryInput = shell.querySelector("[data-exp-query]");
  var kindSelect = shell.querySelector("[data-exp-kind]");
  var catSelect = shell.querySelector("[data-exp-category]");
  var ceilSelect = shell.querySelector("[data-exp-ceiling]");
  var harnSelect = shell.querySelector("[data-exp-harness]");
  var resetBtn = shell.querySelector("[data-exp-reset]");
  var moreBtn = shell.querySelector("[data-exp-more]");
  var statusEl = shell.querySelector("[data-exp-status]");
  var resultsEl = shell.querySelector("[data-exp-results]");
  var tabs = Array.prototype.slice.call(shell.querySelectorAll("[data-exp-tab]"));
  var openEcoBtn = document.querySelector("[data-open-ecosystem]");
  if (!controls || !resultsEl) return;

  // F31-005: twelve results at a time keep the page short enough for Chrome to paint at device scale 1.5.
  var PAGE_SIZE = 12;
  var activeTab = "library";
  var shownLimit = PAGE_SIZE;
  var labels = data.labels || {};
  var harnessMap = data.harnesses || {};
  var ceilingMap = data.ceilings || {};

  function el(tag, cls, txt) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (txt !== undefined && txt !== null) node.textContent = String(txt);
    return node;
  }

  function formatHarnesses(ids) {
    if (!ids || !ids.length) return labels.human_only || "Human steward";
    return ids.map(function (id) { return harnessMap[id] || id; }).join(", ");
  }

  function syncScopeOptions(selectEl) {
    var opts = Array.prototype.slice.call(selectEl.options);
    var currentValid = false;
    opts.forEach(function (opt) {
      var scope = opt.getAttribute("data-scope");
      var hide = Boolean(scope && scope !== activeTab);
      opt.hidden = hide;
      opt.disabled = hide;
      if (!hide && opt.value === selectEl.value) currentValid = true;
    });
    if (!currentValid) {
      for (var i = 0; i < opts.length; i++) {
        if (!opts[i].hidden) { selectEl.value = opts[i].value; break; }
      }
    }
  }

  function makeChipList(values, tone) {
    var ul = el("ul", "chips " + tone);
    values.forEach(function (val) {
      ul.appendChild(el("li", "", val));
    });
    return ul;
  }

  function renderLibraryCard(item) {
    var li = el("li", "exp-card exp-kind-" + item.kind);
    var meta = el("p", "exp-card-meta");
    var pillTone = item.kind === "noun" ? " noun" : (item.kind === "verb" ? " verb" : "");
    meta.appendChild(el("span", "exp-pill" + pillTone, labels[item.kind] || item.kind));
    meta.appendChild(el("span", "", labels.proposal || "Proposal"));
    meta.appendChild(el("span", "", "· " + item.category_label));
    li.appendChild(meta);

    var h3 = el("h3", "exp-card-title");
    var link = el("a", "exp-card-link", item.title);
    link.href = item.url;
    h3.appendChild(link);
    li.appendChild(h3);

    var sub = el("p", "exp-card-sub");
    sub.appendChild(el("code", "", item.subtype));
    li.appendChild(sub);

    li.appendChild(el("p", "exp-card-summary", item.summary));

    var specs = el("div", "exp-card-group");
    var specChips = [
      (labels.ceiling_prefix || "Ceiling:") + " " + (ceilingMap[item.ceiling] || item.ceiling),
      (labels.harnesses_prefix || "Harnesses:") + " " + formatHarnesses(item.harnesses)
    ];
    specs.appendChild(makeChipList(specChips, "plain"));
    li.appendChild(specs);

    var foot = el("p", "exp-card-foot");
    var left = el("span", "");
    if (item.kind === "pack") {
      left.textContent = item.nouns + " nouns · " + item.verbs + " verbs ";
      var jump = el("a", "", labels.open_card || "Jump to pack");
      jump.href = item.anchor;
      left.appendChild(jump);
    } else {
      left.textContent = (labels.pack_ref || "In pack:") + " ";
      var pjump = el("a", "", item.pack_title || item.pack_id);
      pjump.href = item.anchor;
      left.appendChild(pjump);
    }
    foot.appendChild(left);
    var src = el("a", "", labels.open_source || "View JSON source");
    src.href = item.url;
    foot.appendChild(src);
    li.appendChild(foot);
    return li;
  }

  function renderProjectCard(proj) {
    var li = el("li", "exp-card exp-kind-project");
    var meta = el("p", "exp-card-meta");
    meta.appendChild(el("span", "exp-pill", "#" + proj.rank + " · " + proj.track));
    meta.appendChild(el("span", "", labels.scan_mapping || "Public-scan decomposition"));
    meta.appendChild(el("span", "", "· " + proj.category));
    li.appendChild(meta);

    var h3 = el("h3", "exp-card-title");
    var link = el("a", "exp-card-link", proj.repo);
    link.href = proj.url;
    h3.appendChild(link);
    li.appendChild(h3);

    li.appendChild(el("p", "exp-card-summary", proj.summary));

    if (proj.tasks && proj.tasks.length) {
      var vGroup = el("div", "exp-card-group");
      vGroup.appendChild(el("p", "exp-card-label", labels.tasks_label || "Candidate Tasks (verbs):"));
      vGroup.appendChild(makeChipList(proj.tasks, "verb"));
      li.appendChild(vGroup);
    }

    if (proj.task_objects && proj.task_objects.length) {
      var nGroup = el("div", "exp-card-group");
      nGroup.appendChild(el("p", "exp-card-label", labels.objects_label || "Candidate Task Objects (nouns):"));
      nGroup.appendChild(makeChipList(proj.task_objects, "noun"));
      li.appendChild(nGroup);
    }

    var stackTags = (proj.models || []).slice();
    if (proj.language) stackTags.push(proj.language);
    stackTags.push((labels.ceiling_prefix || "Ceiling:") + " " + (ceilingMap[proj.ceiling] || proj.ceiling));
    var sGroup = el("div", "exp-card-group");
    sGroup.appendChild(el("p", "exp-card-label", labels.models_label || "Meta & AI stack:"));
    sGroup.appendChild(makeChipList(stackTags, "plain"));
    li.appendChild(sGroup);

    var foot = el("p", "exp-card-foot");
    foot.appendChild(el("span", "", (labels.harnesses_prefix || "Harnesses:") + " " + formatHarnesses(proj.harnesses)));
    var repoLink = el("a", "", labels.open_repo || "Open repository");
    repoLink.href = proj.url;
    foot.appendChild(repoLink);
    li.appendChild(foot);
    return li;
  }

  function matchesTokens(haystack, tokens) {
    if (!tokens.length) return true;
    var low = haystack.toLowerCase();
    for (var i = 0; i < tokens.length; i++) {
      if (low.indexOf(tokens[i]) === -1) return false;
    }
    return true;
  }

  function filteredItems() {
    var rawQ = (queryInput.value || "").trim().toLowerCase();
    var tokens = rawQ ? rawQ.split(/\s+/) : [];
    var kind = kindSelect.value;
    var cat = catSelect.value;
    var ceil = ceilSelect.value;
    var harn = harnSelect.value;

    if (activeTab === "library") {
      return (data.items || []).filter(function (item) {
        if (kind !== "all" && item.kind !== kind) return false;
        if (cat !== "all" && item.category !== cat) return false;
        if (ceil !== "all" && item.ceiling !== ceil) return false;
        if (harn !== "all" && (!item.harnesses || item.harnesses.indexOf(harn) === -1)) return false;
        if (!tokens.length) return true;
        var blob = [item.title, item.summary, item.subtype, item.pack_id, item.pack_title || "", item.category_label].join(" ");
        return matchesTokens(blob, tokens);
      });
    }

    return (data.projects || []).filter(function (proj) {
      if (kind === "open-weights") {
        var hasOw = (proj.models || []).some(function (m) { return m.toLowerCase().indexOf("open weights") !== -1; });
        if (!hasOw) return false;
      } else if (kind !== "all" && proj.track !== kind) {
        return false;
      }
      if (cat !== "all" && proj.category_id !== cat) return false;
      if (ceil !== "all" && proj.ceiling !== ceil) return false;
      if (harn !== "all" && (!proj.harnesses || proj.harnesses.indexOf(harn) === -1)) return false;
      if (!tokens.length) return true;
      var blob = [
        proj.repo, proj.summary, proj.category, proj.track, proj.language || "",
        (proj.models || []).join(" "), (proj.tasks || []).join(" "), (proj.task_objects || []).join(" ")
      ].join(" ");
      return matchesTokens(blob, tokens);
    });
  }

  function updateView() {
    var matches = filteredItems();
    var slice = matches.slice(0, shownLimit);
    resultsEl.textContent = "";
    if (!matches.length) {
      resultsEl.appendChild(el("li", "exp-empty", labels.empty || "No matching items found."));
    } else {
      var frag = document.createDocumentFragment();
      slice.forEach(function (entry) {
        frag.appendChild(activeTab === "library" ? renderLibraryCard(entry) : renderProjectCard(entry));
      });
      resultsEl.appendChild(frag);
    }
    if (statusEl) {
      if (activeTab === "library") {
        var pCount = 0, vCount = 0, nCount = 0;
        matches.forEach(function (x) {
          if (x.kind === "pack") pCount++;
          else if (x.kind === "verb") vCount++;
          else if (x.kind === "noun") nCount++;
        });
        statusEl.textContent = "Showing " + slice.length + " of " + matches.length +
          " matching library artifacts (" + pCount + " Seed Packs · " + vCount + " Tasks · " + nCount + " Task Objects)";
      } else {
        statusEl.textContent = "Showing " + slice.length + " of " + matches.length +
          " matching Meta Hackathon 2026 repositories (static public-scan decomposition)";
      }
    }
    if (moreBtn) {
      moreBtn.hidden = slice.length >= matches.length;
    }
  }

  function setTab(nextTab) {
    activeTab = nextTab === "ecosystem" ? "ecosystem" : "library";
    shownLimit = PAGE_SIZE;
    tabs.forEach(function (tab) {
      tab.setAttribute("aria-selected", tab.getAttribute("data-exp-tab") === activeTab ? "true" : "false");
    });
    syncScopeOptions(kindSelect);
    syncScopeOptions(catSelect);
    updateView();
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      setTab(tab.getAttribute("data-exp-tab"));
    });
  });

  [queryInput, kindSelect, catSelect, ceilSelect, harnSelect].forEach(function (ctrl) {
    if (!ctrl) return;
    var evt = ctrl.tagName === "INPUT" ? "input" : "change";
    ctrl.addEventListener(evt, function () {
      shownLimit = PAGE_SIZE;
      updateView();
    });
  });

  if (resetBtn) {
    resetBtn.addEventListener("click", function () {
      queryInput.value = "";
      kindSelect.value = "all";
      catSelect.value = "all";
      ceilSelect.value = "all";
      harnSelect.value = "all";
      shownLimit = PAGE_SIZE;
      updateView();
    });
  }

  if (moreBtn) {
    moreBtn.addEventListener("click", function () {
      shownLimit += PAGE_SIZE;
      updateView();
    });
  }

  if (openEcoBtn) {
    openEcoBtn.hidden = false;
    openEcoBtn.addEventListener("click", function () {
      setTab("ecosystem");
      shell.scrollIntoView({ behavior: "smooth", block: "start" });
      if (queryInput) queryInput.focus();
    });
  }

  window.addEventListener("hashchange", function () {
    if (location.hash === "#ecosystem-explorer") setTab("ecosystem");
  });

  controls.hidden = false;
  if (location.hash === "#ecosystem-explorer") {
    setTab("ecosystem");
  } else {
    setTab("library");
  }
})();
