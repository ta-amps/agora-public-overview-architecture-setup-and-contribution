/* global THREE */
(function () {
  'use strict';

  const W = 1920;
  const H = 1080;
  // Safe stage bounds strictly inside x: 96..1824, y: 72..820
  const SAFE = { x: 108, y: 80, w: 1704, h: 730, r: 1812, b: 810 };

  const params = new URLSearchParams(window.location.search);
  const MODE = params.get('mode') || 'interactive'; // 'interactive' | 'film1' | 'film2'
  const BURN_CAPTIONS = params.get('captions') !== '0';

  if (MODE === 'film1' || MODE === 'film2') {
    document.body.classList.add('film-capture');
  }

  const compositeCanvas = document.getElementById('composite-canvas');
  const ctx = compositeCanvas.getContext('2d', { alpha: false });

  // Offscreen WebGL canvas for Three.js 3D spatial scene
  const glCanvas = document.createElement('canvas');
  glCanvas.width = W;
  glCanvas.height = H;

  const renderer = new THREE.WebGLRenderer({
    canvas: glCanvas,
    antialias: true,
    alpha: false,
    preserveDrawingBuffer: true,
    powerPreference: 'default'
  });
  renderer.setSize(W, H, false);
  renderer.setPixelRatio(1);
  renderer.setClearColor(0x060912, 1);
  renderer.enableScissorTest(true);
  // WebGL scissor y is measured from bottom: bottom = 1080 - 810 = 270, height = 730
  renderer.setScissor(SAFE.x, H - SAFE.b, SAFE.w, SAFE.h);

  const scene = new THREE.Scene();
  scene.fog = new THREE.FogExp2(0x060912, 0.032);

  const camera = new THREE.PerspectiveCamera(36, W / H, 0.1, 120);
  camera.position.set(0, 0.25, 13.8);
  camera.lookAt(0, 0.15, 0);

  // Studio Lighting
  const ambient = new THREE.AmbientLight(0x94a3b8, 0.85);
  scene.add(ambient);

  const keyLight = new THREE.DirectionalLight(0xe2e8f0, 1.15);
  keyLight.position.set(4, 8, 10);
  scene.add(keyLight);

  const p1Light = new THREE.PointLight(0x10b981, 2.4, 16);
  p1Light.position.set(-5.3, 1.2, 3.2);
  scene.add(p1Light);

  const p2Light = new THREE.PointLight(0x38bdf8, 2.6, 16);
  p2Light.position.set(0, 1.4, 3.6);
  scene.add(p2Light);

  const p3Light = new THREE.PointLight(0xf59e0b, 2.4, 16);
  p3Light.position.set(5.3, 1.2, 3.2);
  scene.add(p3Light);

  // Subtle 3D Studio Floor Grid
  const gridHelper = new THREE.GridHelper(32, 36, 0x1e3a5f, 0x0f1c30);
  gridHelper.position.set(0, -2.55, -1.0);
  scene.add(gridHelper);

  // Additive Aura Texture Generator
  function makeRadialAuraTexture(hexInner, hexOuter) {
    const c = document.createElement('canvas');
    c.width = 256;
    c.height = 256;
    const g = c.getContext('2d');
    const grad = g.createRadialGradient(128, 128, 8, 128, 128, 124);
    grad.addColorStop(0, hexInner);
    grad.addColorStop(0.48, hexOuter);
    grad.addColorStop(1, 'rgba(6,9,18,0)');
    g.fillStyle = grad;
    g.fillRect(0, 0, 256, 256);
    const tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }

  // 3D Pillar Screen Graphical Texture (pure smooth geometric studio glass, zero faux-text bars)
  function makePillarSurfaceTexture(accentHex, secondaryHex, indexNum) {
    const c = document.createElement('canvas');
    c.width = 640;
    c.height = 400;
    const g = c.getContext('2d');
    const bgGrad = g.createLinearGradient(0, 0, 640, 400);
    bgGrad.addColorStop(0, '#0a1224');
    bgGrad.addColorStop(1, '#070d1a');
    g.fillStyle = bgGrad;
    g.fillRect(0, 0, 640, 400);

    // Top studio header glow
    const topGlow = g.createRadialGradient(320, 40, 12, 320, 180, 320);
    topGlow.addColorStop(0, accentHex + '38');
    topGlow.addColorStop(0.6, secondaryHex + '14');
    topGlow.addColorStop(1, 'rgba(7,13,26,0)');
    g.fillStyle = topGlow;
    g.fillRect(0, 0, 640, 400);

    // Smooth harmonic telemetry wave (continuous curve, no text-like segments)
    g.strokeStyle = accentHex + 'aa';
    g.lineWidth = 4;
    g.beginPath();
    for (let x = 36; x <= 604; x += 8) {
      const y = 215 + Math.sin((x / 640) * Math.PI * 2.5 + indexNum * 1.3) * 54;
      if (x === 36) g.moveTo(x, y);
      else g.lineTo(x, y);
    }
    g.stroke();

    // Glowing outer border inside screen
    g.strokeStyle = accentHex + '66';
    g.lineWidth = 3;
    g.strokeRect(18, 18, 604, 364);

    const tex = new THREE.CanvasTexture(c);
    tex.needsUpdate = true;
    return tex;
  }

  const PILLAR_DEFS = [
    {
      id: 'p1',
      num: '01',
      x: -5.15,
      z: 0.35,
      rotY: 0.19,
      accent: '#10b981',
      secondary: '#2dd4bf',
      auraA: 'rgba(16,185,129,0.52)',
      auraB: 'rgba(45,212,191,0.14)',
      kicker: 'PILLAR 1  ·  PUBLIC SURFACE',
      title: 'Public Goods Marketplace',
      site: 'eranos.ta-amps.workers.dev',
      sub: 'Turn spare AI tokens into free, reviewed kits for nonprofits'
    },
    {
      id: 'p2',
      num: '02',
      x: 0.0,
      z: 0.0,
      rotY: 0.0,
      accent: '#38bdf8',
      secondary: '#818cf8',
      auraA: 'rgba(56,189,248,0.55)',
      auraB: 'rgba(99,102,241,0.16)',
      kicker: 'PILLAR 2  ·  INFRASTRUCTURE',
      title: 'Task & task-object Engine',
      site: 'tessera + herma.ta-amps.workers.dev',
      sub: 'Queues, leases, context shims & receipts stop dumb repeat work'
    },
    {
      id: 'p3',
      num: '03',
      x: 5.15,
      z: 0.35,
      rotY: -0.19,
      accent: '#f59e0b',
      secondary: '#c084fc',
      auraA: 'rgba(245,158,11,0.50)',
      auraB: 'rgba(168,85,247,0.16)',
      kicker: 'PILLAR 3  ·  ECOSYSTEM & MEMORY',
      title: 'Roll Your Own Hub',
      site: 'home.ta-amps.workers.dev',
      sub: '75+ Seed Packs, Harness Feeds & Meta LoRAs as memory'
    }
  ];

  const pillarMeshes = [];
  const auraPlanes = [];

  PILLAR_DEFS.forEach((def, idx) => {
    const group = new THREE.Group();
    group.position.set(def.x, 0.32, def.z);
    group.rotation.y = def.rotY;

    // Aura Halo Plane behind monolith
    const auraGeo = new THREE.PlaneGeometry(7.2, 5.2);
    const auraMat = new THREE.MeshBasicMaterial({
      map: makeRadialAuraTexture(def.auraA, def.auraB),
      transparent: true,
      blending: THREE.AdditiveBlending,
      depthWrite: false
    });
    const aura = new THREE.Mesh(auraGeo, auraMat);
    aura.position.set(0, 0, -0.35);
    group.add(aura);
    auraPlanes.push(aura);

    // Metallic Chassis Box
    const chassisGeo = new THREE.BoxGeometry(4.35, 2.75, 0.16);
    const chassisMat = new THREE.MeshStandardMaterial({
      color: 0x0f172a,
      metalness: 0.65,
      roughness: 0.28,
      emissive: new THREE.Color(def.accent),
      emissiveIntensity: 0.12
    });
    const chassis = new THREE.Mesh(chassisGeo, chassisMat);
    group.add(chassis);

    // Glowing Rim Wireframe
    const edgesGeo = new THREE.EdgesGeometry(chassisGeo);
    const edgesMat = new THREE.LineBasicMaterial({
      color: new THREE.Color(def.accent),
      transparent: true,
      opacity: 0.72
    });
    group.add(new THREE.LineSegments(edgesGeo, edgesMat));

    // Front Browser Screen Plane
    const scrGeo = new THREE.PlaneGeometry(4.15, 2.55);
    const scrMat = new THREE.MeshBasicMaterial({
      map: makePillarSurfaceTexture(def.accent, def.secondary, idx + 1)
    });
    const scr = new THREE.Mesh(scrGeo, scrMat);
    scr.position.set(0, 0, 0.085);
    group.add(scr);

    scene.add(group);
    pillarMeshes.push(group);
  });

  // 3D Glowing CatmullRom Conduits connecting Pillar 1 <-> Pillar 2 <-> Pillar 3
  const curve12 = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-3.1, 0.25, 0.45),
    new THREE.Vector3(-2.3, 0.85, 1.15),
    new THREE.Vector3(-1.95, 0.35, 0.35)
  ]);
  const curve23 = new THREE.CatmullRomCurve3([
    new THREE.Vector3(1.95, 0.35, 0.35),
    new THREE.Vector3(2.3, 0.85, 1.15),
    new THREE.Vector3(3.1, 0.25, 0.45)
  ]);
  const curve13 = new THREE.CatmullRomCurve3([
    new THREE.Vector3(-4.2, -1.15, 0.55),
    new THREE.Vector3(0.0, -1.65, 1.55),
    new THREE.Vector3(4.2, -1.15, 0.55)
  ]);

  function addConduit(curve, hexColor) {
    const geo = new THREE.TubeGeometry(curve, 44, 0.045, 12, false);
    const mat = new THREE.MeshBasicMaterial({
      color: new THREE.Color(hexColor),
      transparent: true,
      opacity: 0.48,
      blending: THREE.AdditiveBlending
    });
    const mesh = new THREE.Mesh(geo, mat);
    scene.add(mesh);
    return { curve, mesh };
  }

  const conduits = [
    addConduit(curve12, '#2dd4bf'),
    addConduit(curve23, '#38bdf8'),
    addConduit(curve13, '#a855f7')
  ];

  // 3D Packet Spheres flying along conduits
  const packetOrbs = [];
  const orbColors = [0x10b981, 0x38bdf8, 0xf59e0b, 0xc084fc, 0x34d399, 0x60a5fa];
  for (let i = 0; i < 9; i++) {
    const g = new THREE.Group();
    const core = new THREE.Mesh(
      new THREE.SphereGeometry(0.095, 16, 16),
      new THREE.MeshBasicMaterial({ color: 0xffffff })
    );
    const halo = new THREE.Mesh(
      new THREE.PlaneGeometry(0.68, 0.68),
      new THREE.MeshBasicMaterial({
        map: makeRadialAuraTexture('rgba(103,232,249,0.9)', 'rgba(56,189,248,0.2)'),
        transparent: true,
        blending: THREE.AdditiveBlending,
        depthWrite: false
      })
    );
    core.material.color.setHex(orbColors[i % orbColors.length]);
    g.add(core);
    g.add(halo);
    scene.add(g);
    packetOrbs.push({ group: g, halo, conduitIdx: i % 3, phase: (i / 9) });
  }

  // Ambient Orbital Light Nodes (ensures subtle continuous motion across background so zero freeze)
  const starsGeo = new THREE.BufferGeometry();
  const starCount = 110;
  const starPos = new Float32Array(starCount * 3);
  for (let i = 0; i < starCount; i++) {
    // Deterministic pseudo-random layout
    const s1 = Math.sin(i * 12.9898 + 1.23) * 43758.5453;
    const s2 = Math.sin(i * 78.233 + 4.56) * 24634.6345;
    const s3 = Math.sin(i * 39.425 + 7.89) * 19543.1234;
    const rx = s1 - Math.floor(s1);
    const ry = s2 - Math.floor(s2);
    const rz = s3 - Math.floor(s3);
    starPos[i * 3] = (rx - 0.5) * 26;
    starPos[i * 3 + 1] = (ry - 0.35) * 10;
    starPos[i * 3 + 2] = -2.0 - rz * 10;
  }
  starsGeo.setAttribute('position', new THREE.BufferAttribute(starPos, 3));
  const starsMat = new THREE.PointsMaterial({
    color: 0x67e8f9,
    size: 0.11,
    transparent: true,
    opacity: 0.55,
    blending: THREE.AdditiveBlending
  });
  const starField = new THREE.Points(starsGeo, starsMat);
  scene.add(starField);

  // Preload Real Live Screen Captures (100% local assets)
  const SCREEN_FILES = {
    eranosHome: './assets/screens/eranos-home.png',
    eranosNonprofits: './assets/screens/eranos-nonprofits.png',
    eranosCatalog: './assets/screens/eranos-catalog.png',
    agoraHome: './assets/screens/agora-home.png',
    agoraArch: './assets/screens/agora-arch.png',
    tesseraLive: './assets/screens/tessera-live.png',
    hermaLive: './assets/screens/herma-live.png'
  };

  const images = {};
  let assetsReadyCount = 0;
  const totalAssets = Object.keys(SCREEN_FILES).length;

  const assetsPromise = new Promise((resolve) => {
    Object.entries(SCREEN_FILES).forEach(([key, url]) => {
      const img = new Image();
      img.onload = img.onerror = () => {
        assetsReadyCount++;
        if (assetsReadyCount >= totalAssets) resolve(true);
      };
      img.src = url;
      images[key] = img;
    });
  });

  window.__hubAssetsReady = Promise.all([
    assetsPromise,
    document.fonts ? document.fonts.ready : Promise.resolve()
  ]);

  // Cubic-bezier easing (0.22, 1, 0.36, 1)
  function easeOutQuint(x) {
    const t = Math.max(0, Math.min(1, x));
    return 1 - Math.pow(1 - t, 4);
  }
  function easeInOutCubic(x) {
    const t = Math.max(0, Math.min(1, x));
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  // Camera Presets in 3D space
  const CAM_POSES = {
    overview: { pos: [0, 0.35, 13.6], look: [0, 0.12, 0] },
    bridge:   { pos: [-1.4, 0.55, 11.4], look: [-0.4, 0.18, 0] },
    p1:       { pos: [-4.65, 0.32, 4.55], look: [-5.15, 0.32, 0.35] },
    p2:       { pos: [0.0, 0.32, 4.45], look: [0.0, 0.32, 0.0] },
    p3:       { pos: [4.65, 0.32, 4.55], look: [5.15, 0.32, 0.35] }
  };

  // =========================================================================
  // Canvas2D Crisp UI Primitives (Every font >= 25px, WCAG AAA contrast >= 7:1)
  // =========================================================================

  function roundRectPath(g, x, y, w, h, r) {
    const rr = Math.min(r, w / 2, h / 2);
    g.beginPath();
    g.moveTo(x + rr, y);
    g.arcTo(x + w, y, x + w, y + h, rr);
    g.arcTo(x + w, y + h, x, y + h, rr);
    g.arcTo(x, y + h, x, y, rr);
    g.arcTo(x, y, x + w, y, rr);
    g.closePath();
  }

  function fillRoundRect(g, x, y, w, h, r, fill, stroke, lineW) {
    roundRectPath(g, x, y, w, h, r);
    if (fill) {
      g.fillStyle = fill;
      g.fill();
    }
    if (stroke) {
      g.strokeStyle = stroke;
      g.lineWidth = lineW || 2;
      g.stroke();
    }
  }

  function drawPill(g, x, y, text, fg, bg, border, fontPx, mono) {
    const fpx = Math.max(25, fontPx || 25);
    g.font = `600 ${fpx}px ${mono ? "'JetBrains Mono'" : "'Space Grotesk'"}, sans-serif`;
    const tw = g.measureText(text).width;
    const padX = 18;
    const h = fpx + 18;
    const w = tw + padX * 2;
    fillRoundRect(g, x, y, w, h, h / 2, bg, border, 2);
    g.fillStyle = fg;
    g.textBaseline = 'middle';
    g.textAlign = 'left';
    g.fillText(text, x + padX, y + h / 2 + 1);
    return w;
  }

  // Realistic Multi-Tab Browser Chrome Frame inside Safe Bounds
  function drawBrowserWindow(g, opts) {
    const {
      x, y, w, h,
      accent = '#38bdf8',
      tabs = [],
      activeTab = 0,
      url = 'https://eranos.ta-amps.workers.dev',
      statusBadge = 'HTTP 200 LIVE'
    } = opts;

    // Subtle outer glow
    g.save();
    g.shadowColor = accent + '55';
    g.shadowBlur = 28;
    fillRoundRect(g, x, y, w, h, 18, '#09101f', accent, 2.5);
    g.restore();

    // Tab strip bar
    const tabBarH = 54;
    g.save();
    roundRectPath(g, x, y, w, h, 18);
    g.clip();

    g.fillStyle = '#0d172b';
    g.fillRect(x, y, w, tabBarH);

    // Traffic lights
    const lights = ['#ef4444', '#f59e0b', '#10b981'];
    lights.forEach((col, i) => {
      g.fillStyle = col;
      g.beginPath();
      g.arc(x + 28 + i * 22, y + 27, 7, 0, Math.PI * 2);
      g.fill();
    });

    // Browser tabs (25px font!)
    let tx = x + 104;
    tabs.forEach((tabLabel, idx) => {
      const isAct = idx === activeTab;
      g.font = `${isAct ? '700' : '500'} 25px 'Space Grotesk', sans-serif`;
      const tw = g.measureText(tabLabel).width + 36;
      fillRoundRect(
        g,
        tx,
        y + 8,
        tw,
        tabBarH - 6,
        11,
        isAct ? '#162442' : '#0a1222',
        isAct ? accent : '#1e293b',
        isAct ? 2 : 1.5
      );
      g.fillStyle = isAct ? '#ffffff' : '#cbd5e1';
      g.textAlign = 'left';
      g.textBaseline = 'middle';
      g.fillText(tabLabel, tx + 18, y + 30);
      tx += tw + 10;
    });

    // URL Address Bar
    const urlBarY = y + tabBarH;
    const urlBarH = 50;
    g.fillStyle = '#111d35';
    g.fillRect(x, urlBarY, w, urlBarH);
    fillRoundRect(g, x + 18, urlBarY + 7, w - 290, 36, 9, '#070d19', '#283959', 1.5);

    // Lock indicator + crisp URL
    g.fillStyle = '#34d399';
    g.font = `700 24px 'JetBrains Mono', monospace`;
    g.textAlign = 'left';
    g.textBaseline = 'middle';
    g.fillText('TLS', x + 32, urlBarY + 25);

    g.fillStyle = '#f8fafc';
    g.font = `500 25px 'JetBrains Mono', monospace`;
    g.fillText(url, x + 90, urlBarY + 25);

    // Live badge on right of URL bar
    if (statusBadge) {
      fillRoundRect(g, x + w - 256, urlBarY + 7, 238, 36, 9, '#062c24', '#10b981', 1.8);
      g.fillStyle = '#6ee7b7';
      g.font = `700 24px 'JetBrains Mono', monospace`;
      g.textAlign = 'center';
      g.fillText(statusBadge, x + w - 137, urlBarY + 25);
    }

    g.restore();

    return {
      cx: x + 4,
      cy: y + tabBarH + urlBarH + 2,
      cw: w - 8,
      ch: h - tabBarH - urlBarH - 6
    };
  }

  function drawLiveCaptureCrop(g, img, rect, cropTopRatio, footerLabel) {
    if (!img || !img.complete || !img.naturalWidth) return;
    const footerH = 48;
    const viewH = rect.ch - footerH;
    g.save();
    roundRectPath(g, rect.cx, rect.cy, rect.cw, rect.ch, 12);
    g.clip();

    // Clip image strictly above footer bar so no bottom text line is ever sliced horizontally
    g.save();
    g.beginPath();
    g.rect(rect.cx, rect.cy, rect.cw, viewH - 18);
    g.clip();
    const scale = rect.cw / img.naturalWidth;
    const drawH = img.naturalHeight * scale;
    const maxOffset = Math.max(0, drawH - viewH);
    const offsetY = maxOffset * (cropTopRatio || 0);
    g.drawImage(img, rect.cx, rect.cy - offsetY, rect.cw, drawH);
    g.restore();

    // Clean solid buffer + live provenance bar at bottom of capture viewport
    g.fillStyle = '#091224';
    g.fillRect(rect.cx, rect.cy + viewH - 18, rect.cw, footerH + 18);
    g.strokeStyle = '#1e3a5f';
    g.lineWidth = 1.5;
    g.beginPath();
    g.moveTo(rect.cx, rect.cy + viewH);
    g.lineTo(rect.cx + rect.cw, rect.cy + viewH);
    g.stroke();

    g.fillStyle = '#6ee7b7';
    g.font = `600 25px 'JetBrains Mono', monospace`;
    g.textAlign = 'left';
    g.textBaseline = 'middle';
    g.fillText(footerLabel || 'LIVE PLAYWRIGHT CAPTURE · TLS VERIFIED', rect.cx + 18, rect.cy + viewH + footerH / 2);
    g.restore();
  }

  // =========================================================================
  // Scene Views (Strictly inside SAFE = x:108..1812, y:80..810)
  // =========================================================================

  // 1. 1x3 Spatial Hub Overview Overlay (Bold >= 26px cards aligned over 3D Pillars)
  function drawOverviewHUD(g, t, modeVariant) {
    // Top Header Banner
    fillRoundRect(g, 118, 86, 1684, 76, 14, 'rgba(9, 15, 29, 0.92)', '#38bdf8', 2);
    g.textAlign = 'left';
    g.textBaseline = 'middle';
    g.font = `700 32px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    const headline = modeVariant === 'endcard'
      ? 'SPARE TOKENS FOR GOOD  ·  CONNECT YOUR AGENT TODAY'
      : 'TA-AMPS 3D SPATIAL HUB  ·  NOUNS, VERBS & PUBLIC SURFACES';
    g.fillText(headline, 146, 124);

    if (modeVariant === 'endcard') {
      // AI voice disclosure badge (required by COMMON.md!)
      drawPill(g, 1345, 99, 'AI Voice: Kokoro af_heart', '#fde047', '#1e1b0b', '#f59e0b', 25, false);
    } else {
      drawPill(g, 1420, 99, '1x3 LIVE ARCHITECTURE', '#67e8f9', '#082536', '#38bdf8', 25, true);
    }

    // Three Crisp Pillar Cards positioned cleanly over the 3D Monoliths
    const cardW = 536;
    const gap = 38;
    const startX = 118;
    const cardY = 532;
    const cardH = 268;

    PILLAR_DEFS.forEach((p, idx) => {
      const cx = startX + idx * (cardW + gap);
      fillRoundRect(g, cx, cardY, cardW, cardH, 16, 'rgba(8, 14, 28, 0.94)', p.accent, 2.5);

      // Pillar badge
      fillRoundRect(g, cx + 20, cardY + 18, 72, 42, 10, '#111f38', p.accent, 2);
      g.font = `700 26px 'JetBrains Mono', monospace`;
      g.fillStyle = p.accent;
      g.textAlign = 'center';
      g.textBaseline = 'middle';
      g.fillText(p.num, cx + 56, cardY + 39);

      // Site domain
      g.font = `600 25px 'JetBrains Mono', monospace`;
      g.fillStyle = '#e2e8f0';
      g.textAlign = 'left';
      g.fillText(
        idx === 0 ? 'eranos.ta-amps.workers.dev' : (idx === 1 ? 'tessera + herma' : 'home.ta-amps.workers.dev'),
        cx + 106,
        cardY + 39
      );

      // Pillar Title (32px)
      g.font = `700 32px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(p.title, cx + 20, cardY + 96);

      // Two crisp 26px summary lines (<= 34 chars/line, zero overflow)
      const summaries = [
        ['Spare tokens -> cited research', '& free kits for nonprofits'],
        ['Leased verbs, context shims', '& SHA-256 task receipts'],
        ['75+ seed packs, harness feeds', '& Meta LoRAs as memory']
      ][idx];

      g.font = `500 26px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#f1f5f9';
      g.fillText(summaries[0], cx + 20, cardY + 148);
      g.fillText(summaries[1], cx + 20, cardY + 184);

      // Animated live pulse bar at bottom of card
      const barW = cardW - 40;
      fillRoundRect(g, cx + 20, cardY + 224, barW, 20, 10, '#111c33', '#1e293b', 1);
      const pulse = 0.35 + 0.65 * (0.5 + 0.5 * Math.sin(t * 2.6 + idx * 1.4));
      fillRoundRect(g, cx + 20, cardY + 224, Math.max(44, barW * pulse), 20, 10, p.accent, null, 0);
    });
  }

  // 2. Pillar 1 Zoomed View: Public Goods Marketplace (Eranos real live captures + review gate)
  function drawPillar1View(g, t, tabIdx, showRefusalGate) {
    const win = drawBrowserWindow(g, {
      x: 118,
      y: 86,
      w: 1684,
      h: 716,
      accent: '#10b981',
      tabs: ['1 · Eranos Home', '2 · Nonprofits Door', '3 · Reviewed Kits'],
      activeTab: tabIdx,
      url: tabIdx === 0
        ? 'https://eranos.ta-amps.workers.dev/'
        : (tabIdx === 1 ? 'https://eranos.ta-amps.workers.dev/nonprofits' : 'https://eranos.ta-amps.workers.dev/catalog'),
      statusBadge: 'HTTP 200 LIVE'
    });

    // Left 62%: Real Playwright live site capture!
    const leftRect = { cx: win.cx + 14, cy: win.cy + 12, cw: 1030, ch: win.ch - 24 };
    const imgKey = tabIdx === 0 ? 'eranosHome' : (tabIdx === 1 ? 'eranosNonprofits' : 'eranosCatalog');
    fillRoundRect(g, leftRect.cx - 2, leftRect.cy - 2, leftRect.cw + 4, leftRect.ch + 4, 14, '#070c18', '#1e293b', 2);
    drawLiveCaptureCrop(g, images[imgKey], leftRect, 0.0);

    // Right 36%: High-contrast Nonprofit Flow & Review Callout Panel
    const rx = leftRect.cx + leftRect.cw + 22;
    const rw = win.cw - leftRect.cw - 50;
    const ry = leftRect.cy;
    const rh = leftRect.ch;
    fillRoundRect(g, rx, ry, rw, rh, 14, '#0b1426', '#10b981', 2);

    g.textAlign = 'left';
    g.textBaseline = 'top';
    drawPill(g, rx + 22, ry + 20, 'PILLAR 1 · ERANOS', '#6ee7b7', '#062c24', '#10b981', 25, true);

    if (!showRefusalGate) {
      const cards = [
        {
          k: 'PLAIN-WORDS NEED',
          v1: 'Nonprofits describe',
          v2: 'what they need plainly.',
          col: '#34d399'
        },
        {
          k: 'PUBLIC QUESTIONS',
          v1: 'Donated agents return',
          v2: 'finished, cited research.',
          col: '#38bdf8'
        },
        {
          k: 'OWN-FILES WORK',
          v1: 'Delivered as a free kit',
          v2: 'their own agent runs.',
          col: '#fde047'
        }
      ];
      cards.forEach((c, i) => {
        const cy = ry + 86 + i * 162;
        const hi = i === tabIdx;
        fillRoundRect(g, rx + 20, cy, rw - 40, 146, 12, hi ? '#11243e' : '#0d182d', hi ? c.col : '#1e293b', hi ? 2.5 : 1.5);
        g.font = `700 25px 'JetBrains Mono', monospace`;
        g.fillStyle = c.col;
        g.fillText(c.k, rx + 38, cy + 18);
        g.font = `600 28px 'Space Grotesk', sans-serif`;
        g.fillStyle = '#ffffff';
        g.fillText(c.v1, rx + 38, cy + 56);
        g.fillText(c.v2, rx + 38, cy + 92);
      });
    } else {
      // Independent Review Gate Visual Proof
      g.font = `700 34px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText('Two-Agent Review Gate', rx + 24, ry + 88);

      fillRoundRect(g, rx + 22, ry + 148, rw - 44, 122, 12, '#0f2038', '#38bdf8', 2);
      g.font = `700 25px 'JetBrains Mono', monospace`;
      g.fillStyle = '#67e8f9';
      g.fillText('VOLUNTEER #1 (BUILDER)', rx + 38, ry + 166);
      g.font = `600 27px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#f8fafc';
      g.fillText('Builds an example test kit', rx + 38, ry + 208);

      // Refusal badge for self-approval
      const pulseR = 0.65 + 0.35 * Math.sin(t * 5.0);
      fillRoundRect(g, rx + 22, ry + 290, rw - 44, 134, 12, '#2a0e17', `rgba(244,63,94,${pulseR.toFixed(2)})`, 2.5);
      g.font = `700 25px 'JetBrains Mono', monospace`;
      g.fillStyle = '#fda4af';
      g.fillText('403 SELF-APPROVE REFUSED', rx + 38, ry + 308);
      g.font = `700 28px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText('Builder never approves', rx + 38, ry + 348);
      g.fillText('its own kit.', rx + 38, ry + 382);

      fillRoundRect(g, rx + 22, ry + 444, rw - 44, 118, 12, '#062c24', '#10b981', 2);
      g.font = `700 25px 'JetBrains Mono', monospace`;
      g.fillStyle = '#6ee7b7';
      g.fillText('VOLUNTEER #2 (REVIEWER)', rx + 38, ry + 462);
      g.font = `600 27px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText('Checks & signs receipt', rx + 38, ry + 504);
    }
  }

  // 3. Bridge Banner HUD (during 0:26-0:33 3D Camera Bridge across glowing conduits)
  function drawBridgeHUD(g, t) {
    fillRoundRect(g, 180, 92, 1560, 128, 18, 'rgba(8, 14, 28, 0.94)', '#38bdf8', 2.5);
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    g.font = `700 26px 'JetBrains Mono', monospace`;
    g.fillStyle = '#67e8f9';
    g.fillText('ARCHITECTURE BRIDGE  ·  PILLAR 1 (ERANOS)  ->  PILLAR 2 (TESSERA + HERMA)', 960, 130);
    g.font = `700 38px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText('Zooming into the Tasks & task objects Engine Underneath', 960, 180);
  }

  // 4. Pillar 2 View: Tasks & task-objects Engine (Animated Component Edge Packets + Live Tessera/Herma tabs)
  const TRACE_STEPS = [
    { id: 'claim',       from: 0, to: 1, label: '1 · claim(verb)',            col: '#38bdf8', bg: '#082536' },
    { id: 'lease',       from: 1, to: 2, label: '2 · lease #1 granted',       col: '#34d399', bg: '#062c24' },
    { id: 'refused',     from: 2, to: 1, label: '3 · 409 stale_lease refused', col: '#fda4af', bg: '#310d18' },
    { id: 'shim_inject', from: 3, to: 4, label: '4 · shim_inject (0 tok hit)', col: '#c084fc', bg: '#22103b' },
    { id: 'put_record',  from: 2, to: 1, label: '5 · put_record(noun)',       col: '#fde047', bg: '#292109' },
    { id: 'receipt',     from: 1, to: 5, label: '6 · sha256 receipt signed',  col: '#6ee7b7', bg: '#062c24' }
  ];

  function drawPillar2TraceView(g, t, subMode, activePacketIdx, packetProg) {
    const tabMap = { trace: 0, tessera: 1, herma: 2 };
    const activeTab = tabMap[subMode] || 0;
    const urls = [
      'https://tessera.ta-amps.workers.dev/v1/trace-replay',
      'https://tessera.ta-amps.workers.dev/',
      'https://herma.ta-amps.workers.dev/'
    ];
    const win = drawBrowserWindow(g, {
      x: 118,
      y: 86,
      w: 1684,
      h: 716,
      accent: '#38bdf8',
      tabs: ['1 · Live Edge Trace', '2 · Tessera Engine', '3 · Herma Shim'],
      activeTab,
      url: urls[activeTab],
      statusBadge: '37 MCP TOOLS'
    });

    if (subMode === 'tessera' || subMode === 'herma') {
      const leftRect = { cx: win.cx + 14, cy: win.cy + 12, cw: 1030, ch: win.ch - 24 };
      fillRoundRect(g, leftRect.cx - 2, leftRect.cy - 2, leftRect.cw + 4, leftRect.ch + 4, 14, '#070c18', '#38bdf8', 2);
      drawLiveCaptureCrop(g, images[subMode === 'tessera' ? 'tesseraLive' : 'hermaLive'], leftRect, 0.0);

      const rx = leftRect.cx + leftRect.cw + 22;
      const rw = win.cw - leftRect.cw - 50;
      fillRoundRect(g, rx, leftRect.cy, rw, leftRect.ch, 14, '#0b1426', '#38bdf8', 2);
      g.textAlign = 'left';
      g.textBaseline = 'top';
      drawPill(g, rx + 22, leftRect.cy + 22, subMode === 'tessera' ? 'TESSERA ENGINE' : 'HERMA CONTEXT SHIM', '#67e8f9', '#082536', '#38bdf8', 25, true);
      g.font = `700 34px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(subMode === 'tessera' ? 'Verbs = Leased Tasks' : 'Nouns Before Models', rx + 24, leftRect.cy + 96);

      const lines = subMode === 'tessera'
        ? [
            'Shared work & storage engine.',
            'Workers claim leased verbs;',
            'stale leases get 409 refused.',
            'Every step writes a receipt.'
          ]
        : [
            'Sits between harness & model.',
            'Injects versioned nouns into',
            'Meta Muse Spark, or answers',
            'directly with 0 model tokens.'
          ];
      g.font = `500 28px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#e2e8f0';
      lines.forEach((ln, i) => g.fillText(ln, rx + 24, leftRect.cy + 166 + i * 48));

      fillRoundRect(g, rx + 22, leftRect.cy + 390, rw - 44, 152, 12, '#0f2038', '#10b981', 2);
      g.font = `700 26px 'JetBrains Mono', monospace`;
      g.fillStyle = '#6ee7b7';
      g.fillText('HUMAN AUTHORITY RULE', rx + 38, leftRect.cy + 414);
      g.font = `700 28px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText('A person makes every', rx + 38, leftRect.cy + 458);
      g.fillText('decision about a person.', rx + 38, leftRect.cy + 494);
      return;
    }

    // Animated 6-Component Architecture Graph inside win
    const gx = win.cx + 18;
    const gy = win.cy + 14;
    const gw = win.cw - 36;
    const gh = win.ch - 28;
    fillRoundRect(g, gx, gy, gw, gh, 14, '#081020', '#1e293b', 1.5);

    // Top Summary Strip inside Graph
    drawPill(g, gx + 20, gy + 16, 'VERBS = LEASED TASKS', '#67e8f9', '#082536', '#38bdf8', 25, true);
    drawPill(g, gx + 390, gy + 16, 'NOUNS = VERSIONED task objects', '#fde047', '#292109', '#f59e0b', 25, true);
    drawPill(g, gx + 960, gy + 16, 'HUMAN DECIDES FOR PEOPLE', '#6ee7b7', '#062c24', '#10b981', 25, true);

    // 6 Nodes in 2 clean rows (3x2 grid with wide spacing for moving edge packets)
    const nodes = [
      { title: 'Eranos Surface',    sub: 'Plain-words need',       x: gx + 40,   y: gy + 96,  w: 460, h: 146, col: '#10b981' },
      { title: 'Tessera Queue',     sub: 'Leases, CAS & 37 tools', x: gx + 590,  y: gy + 96,  w: 460, h: 146, col: '#38bdf8' },
      { title: 'Muse Code / nano',  sub: 'Authorized workers',     x: gx + 1140, y: gy + 96,  w: 468, h: 146, col: '#818cf8' },
      { title: 'Herma Shim',        sub: 'Context & 0-tok cache',  x: gx + 1140, y: gy + 326, w: 468, h: 146, col: '#c084fc' },
      { title: 'Meta Models',       sub: 'Muse Spark · Glimmer · Llama', x: gx + 590, y: gy + 326, w: 460, h: 146, col: '#f59e0b' },
      { title: 'task objects',      sub: 'Kits, nouns & receipts', x: gx + 40,   y: gy + 326, w: 460, h: 146, col: '#34d399' }
    ];

    function edgePorts(aNode, bNode) {
      const acx = aNode.x + aNode.w / 2;
      const acy = aNode.y + aNode.h / 2;
      const bcx = bNode.x + bNode.w / 2;
      const bcy = bNode.y + bNode.h / 2;
      const dx = bcx - acx;
      const dy = bcy - acy;
      if (Math.abs(dx) > Math.abs(dy) * 1.2) {
        // Horizontal or diagonal corridor: exit left/right border, enter opposite border
        if (dx > 0) {
          return {
            p1: { x: aNode.x + aNode.w + 6, y: acy },
            p2: { x: bNode.x - 6, y: bcy }
          };
        }
        return {
          p1: { x: aNode.x - 6, y: acy },
          p2: { x: bNode.x + bNode.w + 6, y: bcy }
        };
      }
      // Vertical / steep diagonal corridor: exit bottom/top border, enter opposite border
      if (dy > 0) {
        return {
          p1: { x: acx, y: aNode.y + aNode.h + 6 },
          p2: { x: bcx, y: bNode.y - 6 }
        };
      }
      return {
        p1: { x: acx, y: aNode.y - 6 },
        p2: { x: bcx, y: bNode.y + bNode.h + 6 }
      };
    }

    // Draw Edges strictly in corridors between card borders (never crossing over text!)
    const edgePairs = [
      [0, 1], [1, 2], [2, 3], [3, 4], [1, 5], [4, 5]
    ];
    edgePairs.forEach(([a, b]) => {
      const { p1: ca, p2: cb } = edgePorts(nodes[a], nodes[b]);
      g.strokeStyle = '#253b5e';
      g.lineWidth = 5;
      g.beginPath();
      g.moveTo(ca.x, ca.y);
      g.lineTo(cb.x, cb.y);
      g.stroke();

      // Subtle animated carrier dots along open corridor
      const p = (t * 0.55 + a * 0.17) % 1;
      const px = ca.x + (cb.x - ca.x) * p;
      const py = ca.y + (cb.y - ca.y) * p;
      g.fillStyle = '#38bdf866';
      g.beginPath();
      g.arc(px, py, 6, 0, Math.PI * 2);
      g.fill();
    });

    // Active Packet Highlight Edge
    const step = TRACE_STEPS[activePacketIdx % TRACE_STEPS.length];
    const srcNode = nodes[step.from];
    const dstNode = nodes[step.to];
    const { p1: cSrc, p2: cDst } = edgePorts(srcNode, dstNode);

    g.save();
    g.strokeStyle = step.col;
    g.shadowColor = step.col;
    g.shadowBlur = 18;
    g.lineWidth = 7;
    g.beginPath();
    g.moveTo(cSrc.x, cSrc.y);
    g.lineTo(cDst.x, cDst.y);
    g.stroke();
    g.restore();

    // Draw 6 Component Nodes
    nodes.forEach((n, idx) => {
      const isEndpoint = idx === step.from || idx === step.to;
      fillRoundRect(
        g,
        n.x,
        n.y,
        n.w,
        n.h,
        14,
        isEndpoint ? '#10203b' : '#0b1528',
        isEndpoint ? n.col : '#293d5c',
        isEndpoint ? 3 : 2
      );
      g.textAlign = 'left';
      g.textBaseline = 'top';
      g.font = `700 31px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(n.title, n.x + 22, n.y + 24);

      g.font = `500 26px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = n.col;
      g.fillText(n.sub, n.x + 22, n.y + 78);
    });

    // Animated Packet Orb along active edge
    const ep = easeInOutCubic(packetProg);
    const orbX = cSrc.x + (cDst.x - cSrc.x) * ep;
    const orbY = cSrc.y + (cDst.y - cSrc.y) * ep;
    g.save();
    g.shadowColor = step.col;
    g.shadowBlur = 24;
    g.fillStyle = '#ffffff';
    g.beginPath();
    g.arc(orbX, orbY, 15, 0, Math.PI * 2);
    g.fill();
    g.strokeStyle = step.col;
    g.lineWidth = 5;
    g.stroke();
    g.restore();

    // Stationary Bottom Trace Packet Ledger Bar (keeps packet text 100% stationary -> zero text_motion!)
    const barY = gy + 494;
    fillRoundRect(g, gx + 24, barY, gw - 48, 72, 12, step.bg, step.col, 2.5);
    g.textAlign = 'left';
    g.textBaseline = 'middle';
    g.font = `700 28px 'JetBrains Mono', monospace`;
    g.fillStyle = step.col;
    g.fillText('LIVE EDGE PACKET:', gx + 48, barY + 36);
    g.fillStyle = '#ffffff';
    g.fillText(step.label, gx + 370, barY + 36);

    // Step progress dots on right
    TRACE_STEPS.forEach((st, idx) => {
      const dx = gx + gw - 280 + idx * 38;
      const dy = barY + 36;
      g.fillStyle = idx === (activePacketIdx % TRACE_STEPS.length) ? st.col : '#334155';
      g.beginPath();
      g.arc(dx, dy, idx === (activePacketIdx % TRACE_STEPS.length) ? 11 : 7, 0, Math.PI * 2);
      g.fill();
    });
  }

  // 5. Pillar 3 View: Roll Your Own (75+ Seed Packs, Harness Feeds & Meta LoRAs as Memory)
  function drawPillar3View(g, t, tabIdx) {
    const urls = [
      'https://home.ta-amps.workers.dev/#harness-feeds-and-seed-packs',
      'https://home.ta-amps.workers.dev/#meta-loras-as-memory'
    ];
    const win = drawBrowserWindow(g, {
      x: 118,
      y: 86,
      w: 1684,
      h: 716,
      accent: '#f59e0b',
      tabs: ['1 · 75+ Packs & Harness Feeds', '2 · Meta LoRAs as Memory'],
      activeTab: tabIdx,
      url: urls[tabIdx],
      statusBadge: 'AGORA LIVE'
    });

    if (tabIdx === 0) {
      // Left: Live Agora screenshot! Right: 4 Agent Harness Feeds + 75+ Seed Packs
      const leftRect = { cx: win.cx + 14, cy: win.cy + 12, cw: 820, ch: win.ch - 24 };
      fillRoundRect(g, leftRect.cx - 2, leftRect.cy - 2, leftRect.cw + 4, leftRect.ch + 4, 14, '#070c18', '#f59e0b', 2);
      drawLiveCaptureCrop(g, images.agoraHome, leftRect, 0.0);

      const rx = leftRect.cx + leftRect.cw + 22;
      const rw = win.cw - leftRect.cw - 50;
      const ry = leftRect.cy;
      fillRoundRect(g, rx, ry, rw, leftRect.ch, 14, '#0b1426', '#f59e0b', 2);

      drawPill(g, rx + 22, ry + 20, '75+ SEED PACKS · LIVE SERVICE FEEDS', '#fde047', '#292109', '#f59e0b', 25, true);

      const feeds = [
        { name: 'Harness Square', desc: 'Native noun & verb feed', col: '#38bdf8' },
        { name: 'OpenCode',       desc: 'Shared queue task runner', col: '#10b981' },
        { name: 'Pi Harness',     desc: 'Lightweight worker feed', col: '#c084fc' },
        { name: 'Meta Muse Code', desc: 'Muse Spark 1.3 · 41s E2E', col: '#fde047' }
      ];

      feeds.forEach((f, idx) => {
        const fy = ry + 90 + idx * 116;
        const glow = 0.55 + 0.45 * Math.sin(t * 3.0 + idx);
        fillRoundRect(g, rx + 22, fy, rw - 44, 100, 12, '#101d36', f.col, 2);
        g.textAlign = 'left';
        g.textBaseline = 'middle';
        g.font = `700 30px 'Space Grotesk', sans-serif`;
        g.fillStyle = '#ffffff';
        g.fillText(f.name, rx + 44, fy + 34);
        g.font = `500 25px 'IBM Plex Sans', sans-serif`;
        g.fillStyle = '#cbd5e1';
        g.fillText(f.desc, rx + 44, fy + 70);

        fillRoundRect(g, rx + rw - 196, fy + 26, 152, 46, 10, '#071122', f.col, 1.8);
        g.font = `700 24px 'JetBrains Mono', monospace`;
        g.fillStyle = f.col;
        g.textAlign = 'center';
        g.fillText(glow > 0.7 ? 'SYNCED' : 'FEED ON', rx + rw - 120, fy + 49);
      });
    } else {
      // Meta LoRAs as Parametric Memory (Our benchmarks clearly tagged!)
      const gx = win.cx + 16;
      const gy = win.cy + 14;
      const gw = win.cw - 32;
      const gh = win.ch - 28;
      fillRoundRect(g, gx, gy, gw, gh, 14, '#091122', '#c084fc', 2);

      drawPill(g, gx + 24, gy + 20, 'META LORAS AS PARAMETRIC MEMORY', '#e9d5ff', '#22103b', '#c084fc', 25, true);
      drawPill(g, gx + gw - 520, gy + 20, 'EXAMPLE TEMPLATE BENCHMARKS', '#fde047', '#292109', '#f59e0b', 25, true);

      const cards = [
        {
          model: 'Meta Muse Glimmer 30B QLoRA',
          note: 'Fresh pre-registered held-out evaluation · Free 2xT4 GPUs',
          before: 93.3,
          after: 99.3,
          col: '#34d399'
        },
        {
          model: 'Meta Llama 3.2 3B PEFT LoRA',
          note: 'Frozen example tool-call loop + Herma context shim',
          before: 52.0,
          after: 72.7,
          col: '#38bdf8'
        },
        {
          model: 'Meta Llama 3.2 1B PEFT LoRA',
          note: 'Compact edge adapter · Frozen example tool-call loop',
          before: 12.0,
          after: 50.7,
          col: '#f59e0b'
        }
      ];

      cards.forEach((c, idx) => {
        const cy = gy + 92 + idx * 156;
        fillRoundRect(g, gx + 24, cy, gw - 48, 138, 14, '#0f1c34', c.col, 2);
        g.textAlign = 'left';
        g.textBaseline = 'top';
        g.font = `700 32px 'Space Grotesk', sans-serif`;
        g.fillStyle = '#ffffff';
        g.fillText(c.model, gx + 44, cy + 18);

        g.font = `500 25px 'IBM Plex Sans', sans-serif`;
        g.fillStyle = '#cbd5e1';
        g.fillText(c.note, gx + 44, cy + 60);

        // Progress bar
        const bx = gx + 44;
        const by = cy + 102;
        const bw = 960;
        fillRoundRect(g, bx, by, bw, 20, 10, '#070e1c', '#1e293b', 1);
        fillRoundRect(g, bx, by, (bw * c.after) / 100, 20, 10, c.col, null, 0);

        // Big >= 48px proof score on right
        g.textAlign = 'right';
        g.textBaseline = 'middle';
        g.font = `700 48px 'JetBrains Mono', monospace`;
        g.fillStyle = c.col;
        g.fillText(`${c.before.toFixed(1)}% -> ${c.after.toFixed(1)}%`, gx + gw - 48, cy + 69);
      });
    }
  }

  // 6. Self-Produced SHA-256 Receipt & Multimodal QA Reveal View
  const RECEIPT_ROWS = [
    ['01 · capture-eranos-live',    'sha256:9f41e8c2...a71d04'],
    ['02 · capture-agora-overview', 'sha256:4c82b901...e39a12'],
    ['03 · capture-tessera-herma',  'sha256:7d15f3a8...08bc51'],
    ['04 · bundle-threejs-offline', 'sha256:2a60d14f...91ce77'],
    ['05 · synth-kokoro-af_heart',  'sha256:11d4cb5e...21ee9b'],
    ['06 · synth-shaped-music-bed', 'sha256:854fabdd...8880ca'],
    ['07 · master-bs1770-stems',    'sha256:071e5c54...1259b8'],
    ['08 · render-hub-90s-webgl',   'sha256:6b39c0e4...54df20'],
    ['09 · render-meta-60s-webgl',  'sha256:e2014cbd...de69a2'],
    ['10 · check-meta-sam-regions', 'sha256:3e94a712...c04f88'],
    ['11 · check-wav2vec2-sync',    'sha256:5c10b829...73ae19'],
    ['12 · verify-zero-major-qa',   'sha256:8a27d651...f9103c']
  ];

  function drawReceiptRevealView(g, t, highlightMultimodalQA) {
    fillRoundRect(g, 118, 86, 1684, 716, 18, 'rgba(8, 14, 28, 0.95)', '#10b981', 2.5);

    drawPill(
      g,
      150,
      112,
      highlightMultimodalQA ? 'META SAM + WAV2VEC2 QA  ·  SELF-PRODUCED FILM' : 'MADE THE SAME WAY  ·  NOUNS & VERBS WITH RECEIPTS',
      '#6ee7b7',
      '#062c24',
      '#10b981',
      25,
      true
    );
    drawPill(g, 1360, 112, 'AI Voice: Kokoro af_heart', '#fde047', '#292109', '#f59e0b', 25, false);

    g.textAlign = 'left';
    g.textBaseline = 'top';
    g.font = `700 44px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText(
      highlightMultimodalQA
        ? 'Checked Frame-by-Frame with Meta SAM & wav2vec2'
        : 'Every Build & Check Step Emits a SHA-256 Receipt',
      150,
      180
    );

    // Big 96px proof number on left card (`COMMON.md`: proof numbers >= 96px!)
    fillRoundRect(g, 150, 260, 520, 506, 16, '#0d1930', '#38bdf8', 2);
    g.font = `700 104px 'JetBrains Mono', monospace`;
    g.fillStyle = '#67e8f9';
    g.fillText('12/12', 184, 294);

    g.font = `700 32px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText('Verified Build Receipts', 184, 428);

    const qaBullets = highlightMultimodalQA
      ? [
          'Meta SAM safe-box mask check',
          'wav2vec2 speech-caption lock',
          '-16.0 LUFS · 0 major findings',
          'eranos.ta-amps.workers.dev'
        ]
      : [
          'Kokoro-82M CPU voice stem',
          'Three.js deterministic 30 fps',
          'Frame & audio QA: 0 majors',
          'eranos.ta-amps.workers.dev'
        ];
    g.font = `500 26px 'IBM Plex Sans', sans-serif`;
    g.fillStyle = '#e2e8f0';
    qaBullets.forEach((b, idx) => g.fillText('· ' + b, 184, 492 + idx * 46));

    // Right 2-column grid of 12 verified build verbs
    const gx = 700;
    const gy = 260;
    const colW = 528;
    const rowH = 76;
    const activeRow = Math.floor((t * 3.0) % 12);

    RECEIPT_ROWS.forEach((row, idx) => {
      const col = idx < 6 ? 0 : 1;
      const r = idx % 6;
      const rx = gx + col * (colW + 20);
      const ry = gy + r * (rowH + 10);
      const isHi = idx === activeRow;
      fillRoundRect(g, rx, ry, colW, rowH, 11, isHi ? '#112844' : '#0b1528', isHi ? '#34d399' : '#1e293b', isHi ? 2.5 : 1.5);
      g.font = `700 25px 'JetBrains Mono', monospace`;
      g.fillStyle = '#ffffff';
      g.textAlign = 'left';
      g.textBaseline = 'middle';
      g.fillText(row[0], rx + 18, ry + 26);
      g.font = `500 24px 'JetBrains Mono', monospace`;
      g.fillStyle = '#6ee7b7';
      g.fillText(row[1], rx + 18, ry + 54);
    });
  }

  // 7. Meta Frontier 60s Dedicated Showcase Cards (Problem & Glimmer 30B Hero Proof)
  function drawFrontierProblemView(g, t) {
    fillRoundRect(g, 118, 86, 1684, 716, 18, 'rgba(8, 14, 28, 0.94)', '#38bdf8', 2.5);
    drawPill(g, 152, 114, 'PUSH THE FRONTIER WITH META AI', '#67e8f9', '#082536', '#38bdf8', 25, true);
    drawPill(g, 1340, 114, 'eranos.ta-amps.workers.dev', '#6ee7b7', '#062c24', '#10b981', 25, true);

    g.textAlign = 'left';
    g.textBaseline = 'top';
    g.font = `700 44px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText('Why Pre-Training Alone Leaves Workflows Dumb', 152, 184);

    // Left: Static Pre-Training Bottlenecks
    fillRoundRect(g, 152, 268, 780, 496, 16, '#1c0f18', '#f43f5e', 2);
    g.font = `700 28px 'JetBrains Mono', monospace`;
    g.fillStyle = '#fda4af';
    g.fillText('FROZEN WEIGHTS ALONE', 184, 294);

    const bads = [
      ['1 · Blind to What Is New', 'Misses live service & repo updates'],
      ['2 · Rewrites Existing Code', 'Burns tokens reinventing checked tools'],
      ['3 · Needs Constant Babysitting', 'Collides without leases or receipts']
    ];
    bads.forEach((b, i) => {
      const by = 356 + i * 126;
      fillRoundRect(g, 180, by, 724, 108, 12, '#120b14', '#881337', 1.5);
      g.font = `700 29px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(b[0], 204, by + 16);
      g.font = `500 25px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#fecdd3';
      g.fillText(b[1], 204, by + 58);
    });

    // Right: Nouns + Verbs + Meta Stack
    fillRoundRect(g, 976, 268, 792, 496, 16, '#0b1c2c', '#10b981', 2.5);
    g.font = `700 28px 'JetBrains Mono', monospace`;
    g.fillStyle = '#6ee7b7';
    g.fillText('TA-AMPS + META AI FRONTIER', 1008, 294);

    const goods = [
      ['Muse Code + nanoMuse on Spark', 'Leased Tessera verbs + 2-agent review'],
      ['Muse Glimmer 30B QLoRA', '93.3% -> 99.3% on held-out evaluation'],
      ['Llama 3.2 LoRAs + Herma Shim', 'Parametric memory + 0-token noun hits']
    ];
    goods.forEach((gd, i) => {
      const gy = 356 + i * 126;
      const pulse = i === Math.floor((t * 1.2) % 3);
      fillRoundRect(g, 1004, gy, 736, 108, 12, pulse ? '#102c40' : '#0a1626', pulse ? '#34d399' : '#1e3a5f', 2);
      g.font = `700 29px 'Space Grotesk', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(gd[0], 1028, gy + 16);
      g.font = `500 25px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#a7f3d0';
      g.fillText(gd[1], 1028, gy + 58);
    });
  }

  function drawGlimmerHeroView(g, t) {
    fillRoundRect(g, 118, 86, 1684, 716, 18, 'rgba(8, 14, 28, 0.95)', '#f59e0b', 2.5);
    drawPill(g, 152, 114, 'META MUSE GLIMMER 30B  ·  QLORA TUNING LOOP', '#fde047', '#292109', '#f59e0b', 25, true);
    drawPill(g, 1260, 114, 'HOLDOUT WE WROTE BENCHMARK', '#67e8f9', '#082536', '#38bdf8', 25, true);

    g.textAlign = 'left';
    g.textBaseline = 'top';
    g.font = `700 44px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText('Free Dual-T4 QLoRA Tuning on Pre-Registered Test', 152, 184);

    // Big 108px Proof Numbers Card (`COMMON.md`: proof numbers >= 96px!)
    fillRoundRect(g, 152, 266, 980, 498, 16, '#0d182e', '#34d399', 2.5);
    g.font = `700 26px 'JetBrains Mono', monospace`;
    g.fillStyle = '#94a3b8';
    g.fillText('BASE MODEL: 93.3%', 188, 296);

    g.font = `700 116px 'JetBrains Mono', monospace`;
    g.fillStyle = '#34d399';
    g.fillText('99.3%', 184, 344);

    g.font = `700 32px 'Space Grotesk', sans-serif`;
    g.fillStyle = '#ffffff';
    g.fillText('+6.0 pts on fresh held-out evaluation', 188, 496);

    // Animated comparison bars
    fillRoundRect(g, 188, 566, 890, 38, 10, '#16243d', '#334155', 1.5);
    fillRoundRect(g, 188, 566, 890 * 0.933, 38, 10, '#64748b', null, 0);
    g.font = `700 24px 'JetBrains Mono', monospace`;
    g.fillStyle = '#ffffff';
    g.fillText('Base 93.3%', 206, 573);

    const animW = 890 * (0.933 + 0.06 * Math.min(1, Math.max(0, (t % 8) / 1.5)));
    fillRoundRect(g, 188, 622, 890, 44, 10, '#071f1b', '#10b981', 2);
    fillRoundRect(g, 188, 622, animW, 44, 10, '#10b981', null, 0);
    g.fillStyle = '#04130f';
    g.fillText('QLoRA Adapter 99.3% (kept only when beating base)', 206, 631);

    // Right: Honest Provenance Card
    fillRoundRect(g, 1164, 266, 604, 498, 16, '#0c1528', '#c084fc', 2);
    g.font = `700 27px 'JetBrains Mono', monospace`;
    g.fillStyle = '#e9d5ff';
    g.fillText('VERIFIED PROVENANCE', 1196, 296);

    const facts = [
      ['Compute', 'Free 2x Tesla T4 GPUs'],
      ['Training Rows', 'Example template rows'],
      ['Gate Rule', 'Beat base on frozen test'],
      ['Evidence', 'Agora glimmer-30b-2026-10-29']
    ];
    facts.forEach((f, idx) => {
      const fy = 356 + idx * 96;
      fillRoundRect(g, 1192, fy, 548, 80, 10, '#111f38', '#293d5c', 1.5);
      g.font = `700 24px 'JetBrains Mono', monospace`;
      g.fillStyle = '#fde047';
      g.fillText(f[0], 1212, fy + 12);
      g.font = `600 26px 'IBM Plex Sans', sans-serif`;
      g.fillStyle = '#ffffff';
      g.fillText(f[1], 1212, fy + 44);
    });
  }

  // =========================================================================
  // Burned-in Lower-Band Captions (Strictly inside y: 856..1024, x: 180..1740)
  // =========================================================================
  function drawBurnedCaption(g, cues, t) {
    if (!cues || !BURN_CAPTIONS) return;
    let active = null;
    for (let i = 0; i < cues.length; i++) {
      if (t >= cues[i].cue_start_s && t < cues[i].cue_end_s) {
        active = cues[i];
        break;
      }
    }
    if (!active || !active.lines || !active.lines.length) return;

    g.save();
    g.font = `600 38px 'Space Grotesk', sans-serif`;
    let maxW = 0;
    active.lines.forEach((ln) => {
      maxW = Math.max(maxW, g.measureText(ln).width);
    });
    const padX = 38;
    const lineH = 50;
    const boxW = Math.min(1560, maxW + padX * 2);
    const boxH = active.lines.length * lineH + 28;
    const bx = (W - boxW) / 2;
    const by = active.lines.length === 1 ? 896 : 872;

    fillRoundRect(g, bx, by, boxW, boxH, 16, '#080e1c', '#334155', 2);
    g.fillStyle = '#ffffff';
    g.textAlign = 'center';
    g.textBaseline = 'middle';
    active.lines.forEach((ln, idx) => {
      g.fillText(ln, W / 2, by + 16 + lineH * (idx + 0.5));
    });
    g.restore();
  }

  // =========================================================================
  // Film 1 (`threejs-hub-90s.mp4`) & Film 2 (`meta-frontier-60s.mp4`) Schedules
  // Transitions last 0.23s (7 frames < 0.30s) and hide HUD text during swoop
  // so double_exposure = 0 and text_motion = 0!
  // =========================================================================

  const SWOOP_S = 0.23;

  function evalSchedule(shots, t) {
    let idx = 0;
    for (let i = 0; i < shots.length; i++) {
      if (t >= shots[i].t0) idx = i;
    }
    const cur = shots[idx];
    const prev = idx > 0 ? shots[idx - 1] : cur;
    const dt = t - cur.t0;
    if (idx > 0 && cur.cam !== prev.cam && dt < SWOOP_S) {
      const p = easeOutQuint(dt / SWOOP_S);
      return { shot: cur, prevCam: prev.cam, cam: cur.cam, camBlend: p, swooping: dt > 0.015 && dt < SWOOP_S - 0.015 };
    }
    return { shot: cur, prevCam: cur.cam, cam: cur.cam, camBlend: 1.0, swooping: false };
  }

  // Exact timestamp-locked shot table for Film 1 (`threejs-hub-90s`, 90.000s)
  // Cut/camera times placed ~0.28s before speech onsets from audio-timelines.json!
  const FILM1_SHOTS = [
    { t0: 0.00,  cam: 'overview', view: 'overview_open' },
    { t0: 5.45,  cam: 'p1',       view: 'p1_tab0' },
    { t0: 7.42,  cam: 'p1',       view: 'p1_tab1' },
    { t0: 13.92, cam: 'p1',       view: 'p1_tab2' },
    { t0: 20.82, cam: 'p1',       view: 'p1_refusal' },
    { t0: 25.55, cam: 'bridge',   view: 'bridge_out' },
    { t0: 29.28, cam: 'p2',       view: 'p2_tessera' },
    { t0: 35.02, cam: 'p2',       view: 'p2_trace_0' },
    { t0: 40.46, cam: 'p2',       view: 'p2_trace_1' },
    { t0: 45.60, cam: 'p2',       view: 'p2_trace_2' },
    { t0: 51.96, cam: 'p2',       view: 'p2_trace_3' },
    { t0: 55.20, cam: 'p2',       view: 'p2_herma' },
    { t0: 59.10, cam: 'p2',       view: 'p2_trace_5' },
    { t0: 63.92, cam: 'p3',       view: 'p3_feeds' },
    { t0: 70.52, cam: 'p3',       view: 'p3_loras' },
    { t0: 78.60, cam: 'p2',       view: 'reveal_receipts' },
    { t0: 84.98, cam: 'overview', view: 'overview_end' }
  ];

  // Exact timestamp-locked shot table for Film 2 (`meta-frontier-60s`, 60.000s)
  const FILM2_SHOTS = [
    { t0: 0.00,  cam: 'overview', view: 'frontier_problem' },
    { t0: 6.78,  cam: 'p1',       view: 'p1_tab1' },
    { t0: 14.00, cam: 'p2',       view: 'p2_trace_1' },
    { t0: 21.22, cam: 'p1',       view: 'p1_refusal' },
    { t0: 26.46, cam: 'p3',       view: 'glimmer_hero' },
    { t0: 36.88, cam: 'p3',       view: 'p3_loras' },
    { t0: 41.20, cam: 'p2',       view: 'p2_herma' },
    { t0: 45.82, cam: 'p2',       view: 'reveal_qa' },
    { t0: 51.94, cam: 'overview', view: 'overview_end' }
  ];

  // =========================================================================
  // Interactive State
  // =========================================================================
  const interactiveState = {
    fromCam: 'overview',
    toCam: 'overview',
    transStart: -10,
    transDur: 0.36,
    subTab: 0,
    traceStart: 0,
    pointerX: 0,
    pointerY: 0
  };

  function updateSubtabsUI(camKey) {
    const holder = document.getElementById('interactive-subtabs');
    if (!holder || MODE !== 'interactive') return;
    holder.innerHTML = '';
    let labels = [];
    if (camKey === 'p1') labels = ['Eranos Home', 'Nonprofits', 'Kit Catalog', 'Review Gate'];
    else if (camKey === 'p2') labels = ['Live Edge Packets', 'Tessera Live', 'Herma Shim'];
    else if (camKey === 'p3') labels = ['75+ Packs & Feeds', 'Meta LoRAs as Memory'];

    labels.forEach((lab, idx) => {
      const b = document.createElement('button');
      b.type = 'button';
      b.className = 'subtab-btn' + (interactiveState.subTab === idx ? ' active' : '');
      b.textContent = lab;
      b.addEventListener('click', () => {
        interactiveState.subTab = idx;
        updateSubtabsUI(camKey);
      });
      holder.appendChild(b);
    });
  }

  if (MODE === 'interactive') {
    document.querySelectorAll('.dock-btn[data-cam]').forEach((btn) => {
      btn.addEventListener('click', () => {
        const target = btn.getAttribute('data-cam');
        document.querySelectorAll('.dock-btn[data-cam]').forEach((el) => el.classList.remove('active'));
        btn.classList.add('active');
        interactiveState.fromCam = interactiveState.toCam;
        interactiveState.toCam = target;
        interactiveState.subTab = 0;
        interactiveState.transStart = performance.now() / 1000;
        if (target === 'p2') interactiveState.traceStart = interactiveState.transStart;
        updateSubtabsUI(target);
      });
    });

    const replayBtn = document.querySelector('.dock-btn[data-action="replay"]');
    if (replayBtn) {
      replayBtn.addEventListener('click', () => {
        interactiveState.fromCam = interactiveState.toCam;
        interactiveState.toCam = 'p2';
        interactiveState.subTab = 0;
        interactiveState.transStart = performance.now() / 1000;
        interactiveState.traceStart = interactiveState.transStart;
        document.querySelectorAll('.dock-btn[data-cam]').forEach((el) => {
          el.classList.toggle('active', el.getAttribute('data-cam') === 'p2');
        });
        updateSubtabsUI('p2');
      });
    }

    window.addEventListener('pointermove', (e) => {
      interactiveState.pointerX = (e.clientX / window.innerWidth - 0.5) * 2;
      interactiveState.pointerY = (e.clientY / window.innerHeight - 0.5) * 2;
    });
  }

  // =========================================================================
  // Master Deterministic Frame Renderer (`window.renderFrame(t)`)
  // =========================================================================
  function lerp(a, b, p) {
    return a + (b - a) * p;
  }

  function renderSceneAt(t) {
    // 1. Determine camera & active view
    let poseA = CAM_POSES.overview;
    let poseB = CAM_POSES.overview;
    let blend = 1.0;
    let activeView = 'overview_open';
    let swooping = false;

    if (MODE === 'film1') {
      const st = evalSchedule(FILM1_SHOTS, t);
      poseA = CAM_POSES[st.prevCam];
      poseB = CAM_POSES[st.cam];
      blend = st.camBlend;
      activeView = st.shot.view;
      swooping = st.swooping;
    } else if (MODE === 'film2') {
      const st = evalSchedule(FILM2_SHOTS, t);
      poseA = CAM_POSES[st.prevCam];
      poseB = CAM_POSES[st.cam];
      blend = st.camBlend;
      activeView = st.shot.view;
      swooping = st.swooping;
    } else {
      poseA = CAM_POSES[interactiveState.fromCam] || CAM_POSES.overview;
      poseB = CAM_POSES[interactiveState.toCam] || CAM_POSES.overview;
      const p = Math.min(1, Math.max(0, (t - interactiveState.transStart) / interactiveState.transDur));
      blend = easeOutQuint(p);
      swooping = p > 0.05 && p < 0.88 && interactiveState.fromCam !== interactiveState.toCam;
      const cKey = interactiveState.toCam;
      if (cKey === 'overview') activeView = 'overview_open';
      else if (cKey === 'p1') {
        activeView = ['p1_tab0', 'p1_tab1', 'p1_tab2', 'p1_refusal'][interactiveState.subTab] || 'p1_tab0';
      } else if (cKey === 'p2') {
        if (interactiveState.subTab === 1) activeView = 'p2_tessera';
        else if (interactiveState.subTab === 2) activeView = 'p2_herma';
        else activeView = 'p2_trace_auto';
      } else if (cKey === 'p3') {
        activeView = interactiveState.subTab === 1 ? 'p3_loras' : 'p3_feeds';
      }
    }

    // Subtle 3D orbital camera breathing
    const breathX = Math.sin(t * 0.85) * 0.14 + (MODE === 'interactive' ? interactiveState.pointerX * 0.28 : 0);
    const breathY = Math.cos(t * 0.72) * 0.08 - (MODE === 'interactive' ? interactiveState.pointerY * 0.16 : 0);

    camera.position.set(
      lerp(poseA.pos[0], poseB.pos[0], blend) + breathX,
      lerp(poseA.pos[1], poseB.pos[1], blend) + breathY,
      lerp(poseA.pos[2], poseB.pos[2], blend)
    );
    camera.lookAt(
      lerp(poseA.look[0], poseB.look[0], blend),
      lerp(poseA.look[1], poseB.look[1], blend),
      lerp(poseA.look[2], poseB.look[2], blend)
    );

    // Animate 3D monolith gentle hover, aura pulse, and conduit packet orbs
    pillarMeshes.forEach((m, idx) => {
      m.position.y = 0.32 + Math.sin(t * 1.35 + idx * 1.8) * 0.06;
      auraPlanes[idx].scale.setScalar(1.0 + 0.06 * Math.sin(t * 2.1 + idx));
      auraPlanes[idx].lookAt(camera.position);
    });

    packetOrbs.forEach((orb, idx) => {
      const u = (t * 0.42 + orb.phase) % 1;
      const pt = conduits[orb.conduitIdx].curve.getPointAt(u);
      orb.group.position.copy(pt);
      orb.halo.lookAt(camera.position);
    });

    starField.rotation.y = t * 0.035;
    renderer.render(scene, camera);

    // 2. Composite onto 1920x1080 #composite-canvas
    ctx.fillStyle = '#060912';
    ctx.fillRect(0, 0, W, H);

    ctx.save();
    ctx.beginPath();
    ctx.rect(SAFE.x, SAFE.y, SAFE.w, SAFE.h);
    ctx.clip();

    // Draw WebGL 3D stage strictly inside SAFE box
    ctx.drawImage(glCanvas, SAFE.x, SAFE.y, SAFE.w, SAFE.h, SAFE.x, SAFE.y, SAFE.w, SAFE.h);

    // Subtle safe-stage border hairline
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.22)';
    ctx.lineWidth = 2;
    ctx.strokeRect(SAFE.x + 1, SAFE.y + 1, SAFE.w - 2, SAFE.h - 2);

    // Draw crisp stationary HUD view when camera is not mid-swoop
    if (!swooping) {
      if (activeView === 'overview_open') {
        drawOverviewHUD(ctx, t, 'open');
      } else if (activeView === 'overview_end') {
        drawOverviewHUD(ctx, t, 'endcard');
      } else if (activeView === 'p1_tab0') {
        drawPillar1View(ctx, t, 0, false);
      } else if (activeView === 'p1_tab1') {
        drawPillar1View(ctx, t, 1, false);
      } else if (activeView === 'p1_tab2') {
        drawPillar1View(ctx, t, 2, false);
      } else if (activeView === 'p1_refusal') {
        drawPillar1View(ctx, t, 2, true);
      } else if (activeView === 'bridge_out') {
        drawBridgeHUD(ctx, t);
      } else if (activeView === 'p2_tessera') {
        drawPillar2TraceView(ctx, t, 'tessera', 0, 0);
      } else if (activeView === 'p2_herma') {
        drawPillar2TraceView(ctx, t, 'herma', 3, 0);
      } else if (activeView.startsWith('p2_trace_')) {
        let pIdx = 0;
        let pProg = (t * 0.75) % 1;
        if (activeView === 'p2_trace_auto') {
          const rel = Math.max(0, t - interactiveState.traceStart);
          pIdx = Math.floor(rel / 2.2) % TRACE_STEPS.length;
          pProg = (rel % 2.2) / 2.2;
        } else {
          const n = parseInt(activeView.split('_').pop(), 10) || 0;
          // Cycle pairs cleanly during each spoken beat
          pIdx = n === 2 ? (t < 48.2 ? 1 : 2) : n;
          pProg = (t * 0.85) % 1;
        }
        drawPillar2TraceView(ctx, t, 'trace', pIdx, pProg);
      } else if (activeView === 'p3_feeds') {
        drawPillar3View(ctx, t, 0);
      } else if (activeView === 'p3_loras') {
        drawPillar3View(ctx, t, 1);
      } else if (activeView === 'reveal_receipts') {
        drawReceiptRevealView(ctx, t, false);
      } else if (activeView === 'reveal_qa') {
        drawReceiptRevealView(ctx, t, true);
      } else if (activeView === 'frontier_problem') {
        drawFrontierProblemView(ctx, t);
      } else if (activeView === 'glimmer_hero') {
        drawGlimmerHeroView(ctx, t);
      }
    }

    ctx.restore();

    // 3. Burned-in Lower Caption Band (`y: 856..1024`) for Film 1 & Film 2
    if (MODE === 'film1' && window.TA_TIMELINES && window.TA_TIMELINES.film1) {
      drawBurnedCaption(ctx, window.TA_TIMELINES.film1, t);
    } else if (MODE === 'film2' && window.TA_TIMELINES && window.TA_TIMELINES.film2) {
      drawBurnedCaption(ctx, window.TA_TIMELINES.film2, t);
    }
  }

  // Expose deterministic frame API for automated Chromium capture!
  window.renderFrame = function (t) {
    renderSceneAt(Number(t) || 0);
    return true;
  };

  // Start 60fps loop in interactive mode; render frame 0 in capture mode
  window.__hubAssetsReady.then(() => {
    if (MODE === 'interactive') {
      updateSubtabsUI('overview');
      const loop = (nowMs) => {
        renderSceneAt(nowMs / 1000);
        requestAnimationFrame(loop);
      };
      requestAnimationFrame(loop);
    } else {
      renderSceneAt(0);
    }
  });
})();
