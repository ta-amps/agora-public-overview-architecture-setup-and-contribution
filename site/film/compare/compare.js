(() => {
  // 1. Agora-compatible Light / Dark Mode ('ta-amps-mode')
  const root = document.documentElement;
  const modeBtn = document.getElementById('mode-toggle');

  function applyMode(mode) {
    root.setAttribute('data-mode', mode);
    if (modeBtn) {
      modeBtn.textContent = mode === 'dark' ? 'Light paper' : 'Dark stage';
    }
    try {
      localStorage.setItem('ta-amps-mode', mode);
    } catch (_) {}
  }

  let initialMode = 'light';
  try {
    const saved = localStorage.getItem('ta-amps-mode');
    if (saved === 'dark' || saved === 'light') {
      initialMode = saved;
    } else if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      initialMode = 'dark';
    }
  } catch (_) {}
  applyMode(initialMode);

  if (modeBtn) {
    modeBtn.addEventListener('click', () => {
      const next = root.getAttribute('data-mode') === 'dark' ? 'light' : 'dark';
      applyMode(next);
    });
  }

  // 2. Architecture Animation Viewer Switcher (16s MP4 / 8s MP4 / Interactive DOM + Safe-Zone Overlay)
  const archVideo = document.getElementById('arch-video');
  const liveWrap = document.getElementById('arch-live-wrap');
  const liveIframe = document.getElementById('arch-live-iframe');
  const safeOverlay = document.getElementById('safe-overlay');
  const overlayBtn = document.getElementById('toggle-safe-overlay');
  const archViewport = document.getElementById('arch-viewport');

  function scaleLiveIframe() {
    if (!archViewport || !liveIframe) return;
    const w = archViewport.clientWidth;
    const scale = w / 1920;
    liveIframe.style.transform = `scale(${scale.toFixed(5)})`;
  }
  window.addEventListener('resize', scaleLiveIframe);

  document.querySelectorAll('[data-arch-tab]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-arch-tab]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      const mode = btn.getAttribute('data-arch-tab');

      if (mode === 'live') {
        if (archVideo) archVideo.pause();
        if (archVideo) archVideo.style.display = 'none';
        if (liveWrap) liveWrap.classList.add('visible');
        if (liveIframe && !liveIframe.getAttribute('src')) {
          liveIframe.setAttribute('src', './arch-anim-live.html?interactive=1&dur=16');
        }
        scaleLiveIframe();
      } else {
        if (liveWrap) liveWrap.classList.remove('visible');
        if (archVideo) {
          archVideo.style.display = 'block';
          const targetSrc = mode === '8s' ? './arch-anim-8s.mp4' : './arch-anim-16s.mp4';
          if (archVideo.getAttribute('data-cur') !== targetSrc) {
            archVideo.setAttribute('data-cur', targetSrc);
            archVideo.src = targetSrc;
            archVideo.load();
          }
          archVideo.play().catch(() => {});
        }
      }
    });
  });

  if (overlayBtn && safeOverlay) {
    overlayBtn.addEventListener('click', () => {
      const on = safeOverlay.classList.toggle('visible');
      overlayBtn.classList.toggle('active', on);
      overlayBtn.textContent = on ? 'Hide Safe-Zone Guide' : 'Show Safe-Zone Guide (y: 96–850 / 880–1000)';
    });
  }

  // 3. Storyboard Suite Filtering & A/B Side-by-Side Comparison
  const suitesGrid = document.getElementById('suites-grid');
  const abControls = document.getElementById('ab-controls');
  const selectA = document.getElementById('ab-select-a');
  const selectB = document.getElementById('ab-select-b');
  const suiteCards = Array.from(document.querySelectorAll('.suite-card'));

  function applySuiteFilter(filter) {
    if (!suitesGrid) return;
    if (filter === 'ab') {
      suitesGrid.classList.add('ab-mode');
      if (abControls) abControls.classList.add('visible');
      updateAB();
    } else {
      suitesGrid.classList.remove('ab-mode');
      if (abControls) abControls.classList.remove('visible');
      suiteCards.forEach((card) => {
        const id = card.getAttribute('data-suite');
        card.style.display = (filter === 'all' || filter === id) ? '' : 'none';
      });
    }
  }

  function updateAB() {
    const a = selectA ? selectA.value : 'S1';
    const b = selectB ? selectB.value : 'S5';
    suiteCards.forEach((card) => {
      const id = card.getAttribute('data-suite');
      card.style.display = (id === a || id === b) ? '' : 'none';
    });
  }

  document.querySelectorAll('[data-suite-filter]').forEach((btn) => {
    btn.addEventListener('click', () => {
      document.querySelectorAll('[data-suite-filter]').forEach((b) => b.classList.remove('active'));
      btn.classList.add('active');
      applySuiteFilter(btn.getAttribute('data-suite-filter'));
    });
  });

  if (selectA) selectA.addEventListener('change', updateAB);
  if (selectB) selectB.addEventListener('change', updateAB);

  // 4. Full-Resolution Contact-Sheet Lightbox
  const lightbox = document.getElementById('lightbox');
  const lbImg = document.getElementById('lb-img');
  const lbTitle = document.getElementById('lb-title');
  const lbClose = document.getElementById('lb-close');

  function openLightbox(src, title) {
    if (!lightbox || !lbImg) return;
    lbImg.src = src;
    if (lbTitle) lbTitle.textContent = title || 'Contact Sheet';
    lightbox.classList.add('open');
  }

  function closeLightbox() {
    if (!lightbox) return;
    lightbox.classList.remove('open');
  }

  document.querySelectorAll('[data-zoom-src]').forEach((el) => {
    el.addEventListener('click', () => {
      openLightbox(el.getAttribute('data-zoom-src'), el.getAttribute('data-zoom-title'));
    });
  });

  if (lbClose) lbClose.addEventListener('click', closeLightbox);
  if (lightbox) {
    lightbox.addEventListener('click', (e) => {
      if (e.target === lightbox) closeLightbox();
    });
  }
  window.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeLightbox();
  });
})();
