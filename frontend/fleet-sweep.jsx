// ColdCall — the fleet sweep. 206 real shipment legs, five lanes in, three
// tracks out, one gate. Everything renders from T; nothing mounts per scene.

const { useComposition, animate, interpolate, Easing, Captions } = window;

const W = 1920, H = 1080;
const INK = 'var(--color-text)', GROUND = 'var(--color-bg)', SURF = 'var(--color-surface)';
const RED = 'var(--color-accent)', N600 = 'var(--color-neutral-600)', N700 = 'var(--color-neutral-700)', N400 = 'var(--color-neutral-400)';
const HATCH = 'repeating-linear-gradient(45deg,' + INK + ' 0 2px,transparent 2px 6px)';

const LANES = [
  { label: 'figshare 14888121 · ULT vaccine containers', n: 39, r: 0, q: 0, d: 39 },
  { label: 'Recherche Data Gouv · mango air cargo', n: 62, r: 0, q: 0, d: 62 },
  { label: 'SOFIE EU H2020 · table grape', n: 3, r: 1, q: 0, d: 2 },
  { label: 'Strawberry truck · 6 shipments, 9 probes', n: 54, r: 2, q: 12, d: 40 },
  { label: 'Zenodo 7907515 · pharma logger LL1', n: 48, r: 10, q: 11, d: 27 },
];

const LANE_Y = [232, 366, 500, 634, 768];
const YARD_X0 = 210, STEP = 19.5, GATE_X = 1276;
const OUT = {
  release:    { x: 1392, y: 196, cols: 5 },
  quarantine: { x: 1392, y: 398, cols: 6 },
  destroy:    { x: 1392, y: 596, cols: 17 },
};
const BAR = { x: 236, y: 470, w: 1448, h: 132 };

// ---- build the 206 legs, real counts per dataset -------------------------
const TRUCKS = [];
const tally = { release: 0, quarantine: 0, destroy: 0 };
LANES.forEach((L, li) => {
  for (let i = 0; i < L.n; i++) {
    const verdict = i < L.r ? 'release' : i < L.r + L.q ? 'quarantine' : 'destroy';
    const o = OUT[verdict], k = tally[verdict]++;
    TRUCKS.push({
      lane: li, i, verdict,
      yx: YARD_X0 + i * STEP, yy: LANE_Y[li],
      ox: o.x + (k % o.cols) * 22, oy: o.y + Math.floor(k / o.cols) * 21,
    });
  }
});
const COUNTS = { release: tally.release, quarantine: tally.quarantine, destroy: tally.destroy };
// bar order: every release, then every hold, then every destroy
const ORDER = { release: 0, quarantine: COUNTS.release, destroy: COUNTS.release + COUNTS.quarantine };
const SEG_W = BAR.w / TRUCKS.length;
const seen = { release: 0, quarantine: 0, destroy: 0 };
TRUCKS.forEach(t => { t.rank = ORDER[t.verdict] + seen[t.verdict]++; t.bx = BAR.x + t.rank * SEG_W; });

// ---- 3D yard geometry (world units, X = travel, Z = lanes) ---------------
const ROWLEN = 30, XSTEP = 3.0, ROWZ = 4.2, LANEGAP = 3.5, X0 = -55;
// each dataset becomes a block of short rows rather than one 62-truck row
let zCursor = -30;
const LANE_Z = LANES.map(L => {
  const z0 = zCursor;
  zCursor += Math.ceil(L.n / ROWLEN) * ROWZ + LANEGAP;
  return z0;
});
const LANE_ROWS = LANES.map(L => Math.ceil(L.n / ROWLEN));
const GATE_X3 = X0 + ROWLEN * XSTEP + 14;
const OUT3 = {
  release:    { x: GATE_X3 + 14, z: -44, cols: 7,  dz: 3.6, dx: 4.4 },
  quarantine: { x: GATE_X3 + 29, z: -44, cols: 8,  dz: 3.6, dx: 4.4 },
  destroy:    { x: GATE_X3 + 50, z: -44, cols: 15, dz: 3.6, dx: 4.4 },
};
const t3 = { release: 0, quarantine: 0, destroy: 0 };
TRUCKS.forEach(t => {
  t.wx = X0 + (t.i % ROWLEN) * XSTEP;
  t.wz = LANE_Z[t.lane] + Math.floor(t.i / ROWLEN) * ROWZ;
  const o = OUT3[t.verdict], k = t3[t.verdict]++;
  t.ox3 = o.x + Math.floor(k / o.cols) * o.dx;
  t.oz3 = o.z + (k % o.cols) * o.dz;
});
// where each truck stands when the blocks have collapsed into the bar: one
// row, ordered release → hold → destroy, trucks turned broadside so the row
// reads as a band. The bar is formed in 3D first, then handed to the plan.
const BSTEP = 1.24, BAR3_W = TRUCKS.length * BSTEP;
TRUCKS.forEach(t => { t.bx3 = -BAR3_W / 2 + t.rank * BSTEP; });

function boxOf(pts) {
  let x0 = 1e9, x1 = -1e9, z0 = 1e9, z1 = -1e9;
  pts.forEach(p => {
    x0 = Math.min(x0, p[0]); x1 = Math.max(x1, p[0] + 2.4);
    z0 = Math.min(z0, p[1]); z1 = Math.max(z1, p[1] + 1.1);
  });
  return [x0, x1, z0, z1];
}
const LANE_BOX = boxOf(TRUCKS.map(t => [t.wx, t.wz]));
const FULL_BOX = boxOf(TRUCKS.map(t => [t.wx, t.wz]).concat(TRUCKS.map(t => [t.ox3, t.oz3])));
const BLOCK_BOX = boxOf(TRUCKS.map(t => [t.ox3, t.oz3]));
const BAR_BOX = boxOf(TRUCKS.map(t => [t.bx3, -1.2]));
// distance that fits the yard to ~86% of a 38° vertical fov at 16:9,
// viewed down a 55° elevation (so the ground plane foreshortens by sin 55°)
const TAN_HALF = Math.tan((38 * Math.PI / 180) / 2), ASPECT = 16 / 9;
// a hard Math.max of the two fit distances puts a kink in the camera path at
// the instant they cross — which reads as a jolt. Round the corner instead.
const smax = (a, b) => {
  const k = 0.08 * Math.max(a, b);
  return 0.5 * (a + b + Math.sqrt((a - b) * (a - b) + k * k));
};
function fitTo(w, d, fill, sinEl) {
  const dV = (d * sinEl / 2) / TAN_HALF;
  const dH = (w / 2) / (TAN_HALF * ASPECT);
  return smax(smax(dV, dH), 30) / fill;
}

// DEMO-0001 is a pharma LL1 leg that came back quarantine / retest
const DEMO = TRUCKS.findIndex(t => t.lane === 4 && t.verdict === 'quarantine');

const fill = v => v === 'release' ? GROUND : v === 'quarantine' ? HATCH : RED;
const lerp = (a, b, u) => a + (b - a) * u;
const ss = k => k * k * (3 - 2 * k);


function FleetSweep() {
  const { T, CUES } = useComposition();

  // ---- three motion helpers, nothing eases outside them ------------------
  const MOTION = {
    enter: (s, e) => animate({ start: s, end: e, ease: Easing.easeOutCubic })(T),
    glide: (s, e) => animate({ start: s, end: e, ease: Easing.easeInOutCubic })(T),
    snap:  (s, e) => animate({ start: s, end: e, ease: Easing.easeInOutQuart })(T),
    glideAt: (tt, s, e) => animate({ start: s, end: e, ease: Easing.easeInOutCubic })(tt),
  };
  const laneInAt = tt => animate({ start: CUES.Lane - 0.3, end: CUES.Lane + 1.1, ease: Easing.easeOutCubic })(tt);
  const fleetInAt = tt => animate({ start: CUES.Fleet - 0.2, end: CUES.Fleet + 1.4, ease: Easing.easeOutCubic })(tt);

  // ---- camera ------------------------------------------------------------
  const scale = interpolate(
    [0, CUES.Windshield, CUES.Lane, CUES.Fleet, CUES.Sweep, CUES.Resolve, CUES.Hold],
    [6.4, 6.4, 5.2, 1.9, 1.0, 1.0, 1.03], Easing.easeInOutCubic)(T);
  const d = TRUCKS[DEMO];
  const fx = interpolate([0, CUES.Windshield, CUES.Lane, CUES.Fleet, CUES.Sweep, CUES.Resolve],
    [d.yx + 8, d.yx + 8, d.yx + 60, 700, 960, 960], Easing.easeInOutCubic)(T);
  const fy = interpolate([0, CUES.Windshield, CUES.Lane, CUES.Fleet, CUES.Sweep, CUES.Resolve],
    [d.yy + 4, d.yy + 4, d.yy, LANE_Y[4], 500, 520], Easing.easeInOutCubic)(T);

  // ---- reveal ------------------------------------------------------------
  const laneIn = MOTION.enter(CUES.Lane - 0.3, CUES.Lane + 1.1);
  const fleetIn = MOTION.enter(CUES.Fleet - 0.2, CUES.Fleet + 1.4);
  const gateIn = MOTION.enter(CUES.Sweep - 0.5, CUES.Sweep + 0.6);
  const gateHot = animate({ from: 0, to: 1, start: CUES.Sweep + 1.4, end: CUES.Sweep + 2.3, ease: Easing.easeOutCubic })(T);
  const barIn = MOTION.glide(CUES.Resolve + 2.1, CUES.Resolve + 2.9);
  const yardOut = MOTION.snap(CUES.Resolve + 0.2, CUES.Resolve + 1.3);


  // ---- drive the 206 real reefer trucks from this same clock -------------
  const truckRef = React.useRef(null);
  const world = React.useMemo(() => {
    const rows = TRUCKS.map((t, idx) => {
      const stg = (t.i / 62) * 0.9 + t.lane * 0.16;
      const u = MOTION.glide(CUES.Sweep + stg, CUES.Resolve - 0.5 + stg * 0.3);
      const rs = (t.rank / TRUCKS.length) * 0.55;
      const bpos = MOTION.glide(CUES.Resolve - 0.2 + rs, CUES.Resolve + 1.15 + rs);
      let x, z;
      if (u < 0.42) { const k = u / 0.42; x = lerp(t.wx, GATE_X3, k); z = t.wz; }
      else if (u < 0.72) { const k = ss((u - 0.42) / 0.3); x = lerp(GATE_X3, t.ox3, k); z = t.wz; }
      else { const k = ss((u - 0.72) / 0.28); x = t.ox3; z = lerp(t.wz, t.oz3, k); }
      const yaw = 0;   // always square to the lane — the fleet reads as a fleet
      const born = idx === DEMO ? 1 : (t.lane === 4 ? Math.max(laneIn, fleetIn) : fleetIn);
      const drop = born > 0.02 ? (1 - ss(Math.min(1, born * 1.5))) * -22 : -60;
      // 0.42 is the gate; the stripe takes its colour over the 0.2 after it
      const decided = Math.max(0, Math.min(1, (u - 0.42) / 0.2));
      if (idx === DEMO) {
        const heroOn = T < CUES.Lane - 0.25;
        return {
          x: lerp(heroOn ? t.wx : x, t.bx3, bpos),
          z: lerp(t.wz, 0, bpos),
          yaw: bpos * Math.PI / 2, verdict: t.verdict,
          lift: heroOn ? -60 : drop, decided,
        };
      }
      // the blocks converge into the bar row while still in 3D
      return {
        x: lerp(x, t.bx3, bpos), z: lerp(z, 0, bpos),
        yaw: bpos * Math.PI / 2, verdict: t.verdict, lift: drop, decided,
      };
    });
    // the camera walks the same path the DOM camera does: windshield → fleet
    const d3 = TRUCKS[DEMO];
    // where the truck is right now, so the chase camera can ride with it
    const arriveC = animate({ start: 0, end: CUES.Windshield + 1.5, ease: Easing.easeOutQuart })(T);
    const tkx = lerp(d3.wx - 168, d3.wx, arriveC);
    const K = [0, CUES.Windshield, CUES.Lane, CUES.Fleet, CUES.Sweep, CUES.Resolve, CUES.Hold];
    // chase alongside → settle on the cab → pull up over the whole yard
    const cxOff = interpolate(K, [-16, 6.2, 17, 0, 0, 0, 0], Easing.easeInOutCubic)(T);
    // the chase ramp must end on the Fleet cue, the same keyframe the height
    // and depth interpolations land on — two blends on different windows
    // compound into an acceleration spike at the handoff
    const chase = interpolate([0, CUES.Windshield, CUES.Lane, CUES.Fleet],
      [1, 1, 1, 0], Easing.easeInOutCubic)(T);
    // lanes → the whole yard → the outcome blocks → the bar, eased
    // these keyframes must line up with the truck timings exactly, or the
    // camera frames one arrangement while the fleet is already in another
    // the frame must cover every truck for as long as any truck is still in
    // transit — trucks arrive in the blocks from ~Gate until Resolve − 0.5
    const BK = [CUES.Fleet - 0.4, CUES.Sweep + 1.0, CUES.Resolve - 0.4, CUES.Resolve + 1.7];
    const box = [0, 1, 2, 3].map(i => interpolate(
      BK, [LANE_BOX[i], FULL_BOX[i], FULL_BOX[i], BAR_BOX[i]],
      Easing.easeInOutCubic)(T));
    const bx0 = box[0], bx1 = box[1], bz0 = box[2], bz1 = box[3];
    const liveCx = (bx0 + bx1) / 2, liveCz = (bz0 + bz1) / 2;
    // 55° over the yard, tipping to 86° — near straight down — as the bar forms,
    // so the 3D view and the flat plan are the same projection at the handoff
    const elDeg = interpolate([CUES.Gate + 1.4, CUES.Resolve + 1.2], [55, 86], Easing.easeInOutCubic)(T);
    const SIN_EL = Math.sin(elDeg * Math.PI / 180), COS_EL = Math.cos(elDeg * Math.PI / 180);
    // the framed box changes shape every frame as trucks bunch and spread, so
    // a fit from one instant twitches. Sample either side of now, keep the
    // widest, average the centre.
    const boxAt = tt => {
      let ax0 = 1e9, ax1 = -1e9, az0 = 1e9, az1 = -1e9, n = 0;
      TRUCKS.forEach((t, idx) => {
        const st = (t.i / 62) * 0.9 + t.lane * 0.16;
        const uu = MOTION.glideAt(tt, CUES.Sweep + st, CUES.Resolve - 0.5 + st * 0.3);
        const r2 = (t.rank / TRUCKS.length) * 0.55;
        const bp = MOTION.glideAt(tt, CUES.Resolve - 0.2 + r2, CUES.Resolve + 1.15 + r2);
        const bn = idx === DEMO ? 1
          : (t.lane === 4 ? Math.max(laneInAt(tt), fleetInAt(tt)) : fleetInAt(tt));
        if (bn <= 0.02) return;
        let xx, zz;
        if (uu < 0.42) { const k = uu / 0.42; xx = lerp(t.wx, GATE_X3, k); zz = t.wz; }
        else if (uu < 0.72) { const k = (uu - 0.42) / 0.3; xx = lerp(GATE_X3, t.ox3, k); zz = t.wz; }
        else { const k = (uu - 0.72) / 0.28; xx = t.ox3; zz = lerp(t.wz, t.oz3, k); }
        xx = lerp(xx, t.bx3, bp); zz = lerp(zz, 0, bp);
        n++;
        ax0 = Math.min(ax0, xx); ax1 = Math.max(ax1, xx + 2.4);
        az0 = Math.min(az0, zz); az1 = Math.max(az1, zz + 1.1);
      });
      return n ? { w: ax1 - ax0, d: az1 - az0, cx: (ax0 + ax1) / 2, cz: (az0 + az1) / 2 } : null;
    };
    // The look-ahead max that used to live here was itself a hard max, so it
    // put a kink in the path at the instant the dominant sample flipped. The
    // eased blend below covers the resolve phase, and during the sweep the
    // box changes smoothly on its own — so sample now, and only now.
    let sw = bx1 - bx0, sd = Math.max(bz1 - bz0, 14), scx = liveCx, scz = liveCz;
    // Once the bar starts forming the live box grows 84 → 265 in about a
    // second, and a fit that chases it reads as a lurch. The bar's framing is
    // known at authoring time, so blend to it on one eased ramp instead.
    const toBar = ss(Math.max(0, Math.min(1, (T - (CUES.Resolve - 1.4)) / 2.9)));
    sw = lerp(sw, BAR3_W + 10, toBar);
    sd = lerp(sd, 26, toBar);
    scx = lerp(scx, 0, toBar);
    scz = lerp(scz, 0, toBar);
    const fitD = fitTo(sw, sd, 0.84, SIN_EL);
    const cxAbs = interpolate(K, [0, 0, 0, scx, scx, scx, scx], Easing.easeInOutCubic)(T);
    const cx = chase * (tkx + cxOff) + (1 - chase) * cxAbs;
    const fitY = fitD * SIN_EL, fitZ = scz + fitD * COS_EL;
    const cy = interpolate(K, [2.6, 1.9, 7.5, fitY, fitY, fitY, fitY * 1.02], Easing.easeInOutCubic)(T);
    const czOff = interpolate(K, [9.5, 4.6, 20, 0, 0, 0, 0], Easing.easeInOutCubic)(T);
    const czAbs = interpolate(K, [0, 0, 0, fitZ, fitZ, fitZ, fitZ * 1.02], Easing.easeInOutCubic)(T);
    const cz = chase * (d3.wz + czOff) + (1 - chase) * czAbs;
    const txAbs = interpolate(K, [0, 0, 0, scx, scx, scx, scx], Easing.easeInOutCubic)(T);
    const tx = chase * (tkx + interpolate(K, [4, 0, 2, 0, 0, 0, 0], Easing.easeInOutCubic)(T))
             + (1 - chase) * txAbs;
    const tz = interpolate(K, [d3.wz, d3.wz, d3.wz, scz, scz, scz, scz], Easing.easeInOutCubic)(T);
    const ty = interpolate(K, [1.6, 1.5, 1.5, 0, 0, 0, 0], Easing.easeInOutCubic)(T);
    const roadOp = 1 - MOTION.enter(CUES.Windshield + 1.2, CUES.Lane + 0.4);
    const arriveR = animate({ start: 0, end: CUES.Windshield + 1.5, ease: Easing.easeOutQuart })(T);
    const hx = lerp(d3.wx - 168, d3.wx, arriveR);
    const rolling = 1 - arriveR;
    return {
      trucks: rows,
      cam: { x: cx, y: cy, z: cz, tx, ty, tz },
      road: { x: 0, z: d3.wz, op: roadOp },
      hero: {
        x: hx, z: d3.wz, x0: d3.wx - 168,
        op: T < CUES.Lane - 0.2 ? 1 : 0,
        // suspension: bob and body-roll only while it is actually moving
        pitch: rolling * Math.sin(T * 9.1) * 0.013,
        roll: rolling * Math.sin(T * 6.3) * 0.017,
      },
    };
  }, [T]);
  React.useEffect(() => {
    const el = truckRef.current;
    if (el && el.seek) el.seek(world);
  }, [world]);
  const showWorld = 1 - MOTION.glide(CUES.Resolve + 1.3, CUES.Resolve + 2.15);

  let landed = 0;
  const marks = TRUCKS.map((t, idx) => {
    const stg = (t.i / 62) * 0.9 + t.lane * 0.16;
    const u = MOTION.glide(CUES.Sweep + stg, CUES.Resolve - 0.5 + stg * 0.3);
    const rs = (t.rank / TRUCKS.length) * 0.55;
    const b = MOTION.glide(CUES.Resolve - 0.2 + rs, CUES.Resolve + 1.15 + rs);
    const bsize = MOTION.glide(CUES.Resolve + 2.05, CUES.Resolve + 3.0);
    if (u > 0.98) landed++;

    // five lanes in, one gate, three tracks out
    let x, y;
    if (u < 0.42) { const k = u / 0.42; x = lerp(t.yx, GATE_X, k); y = t.yy; }
    else if (u < 0.72) { const k = ss((u - 0.42) / 0.3); x = lerp(GATE_X, t.ox, k); y = t.yy; }
    else { const k = ss((u - 0.72) / 0.28); x = t.ox; y = lerp(t.yy, t.oy, k); }
    x = lerp(x, t.bx, b); y = lerp(y, BAR.y, b);

    const w = lerp(16, SEG_W - 0.6, bsize), h = lerp(9, BAR.h, bsize);
    const op = idx === DEMO ? 1 : (t.lane === 4 ? Math.max(laneIn, fleetIn) : fleetIn);
    const decided = Math.max(0, Math.min(1, (u - 0.42) / 0.2));

    return React.createElement('div', {
      key: idx,
      style: {
        position: 'absolute', left: 0, top: 0,
        transform: 'translate(' + x + 'px,' + y + 'px)',
        width: w, height: h, opacity: op,
        background: decided > 0.5 ? fill(t.verdict) : 'var(--color-neutral-400)',
        border: decided > 0.5 && t.verdict === 'destroy' ? 'none' : '1.5px solid ' + INK,
        boxShadow: idx === DEMO && T < CUES.Sweep ? '0 0 0 3px ' + RED : 'none',
      },
    });
  });

  const rail = (label, y, n, v) => React.createElement('div', {
    style: {
      position: 'absolute', left: OUT[v].x, top: y, width: 420,
      opacity: MOTION.enter(CUES.Sweep + 2.4, CUES.Gate + 0.4) * (1 - barIn), display: 'flex', alignItems: 'baseline', gap: 10,
      fontFamily: 'IBM Plex Mono, monospace', fontSize: 17, letterSpacing: '.12em',
      textTransform: 'uppercase', color: v === 'destroy' ? RED : INK, fontWeight: 600,
    },
  }, label, React.createElement('span', { style: { fontSize: 26, letterSpacing: '-.02em' } }, n));

  return React.createElement('div',
    { style: { position: 'absolute', inset: 0, background: GROUND, overflow: 'hidden', fontFamily: 'Archivo, system-ui, sans-serif', color: INK } },

    React.createElement('fleet-trucks', {
      ref: truckRef,
      style: { position: 'absolute', inset: 0, opacity: showWorld, pointerEvents: 'none' },
    }),

    // ---- the flat plan, which takes over once the bar forms ----
    React.createElement('div', {
      style: {
        position: 'absolute', left: 0, top: 0, width: W, height: H,
        transformOrigin: '0 0',
        transform: 'translate(' + (W / 2 - fx * scale) + 'px,' + (H / 2 - fy * scale) + 'px) scale(' + scale + ')',
        opacity: 1 - showWorld,
      },
    },
      // lane rules + labels
      LANES.map((L, i) => React.createElement('div', { key: 'l' + i },
        React.createElement('div', {
          style: {
            position: 'absolute', left: 150, top: LANE_Y[i] + 20, width: 1130, height: 2,
            background: N400, opacity: (i === 4 ? Math.max(laneIn, fleetIn) : fleetIn) * (1 - yardOut),
          },
        }),
        React.createElement('div', {
          style: {
            position: 'absolute', left: 150, top: LANE_Y[i] - 20, width: 700,
            fontFamily: 'IBM Plex Mono, monospace', fontSize: 12, letterSpacing: '.1em',
            textTransform: 'uppercase', color: N700,
            opacity: (i === 4 ? Math.max(laneIn, fleetIn) : fleetIn) * (1 - yardOut),
          },
        }, L.label + ' · ' + L.n + ' legs')
      )),

      // the gate
      React.createElement('div', {
        style: {
          position: 'absolute', left: GATE_X + 24, top: 150, width: 3, height: 700,
          background: gateHot > 0.5 ? RED : INK, opacity: gateIn * (1 - yardOut),
        },
      }),
      React.createElement('div', {
        style: {
          position: 'absolute', left: GATE_X + 36, top: 118, opacity: gateIn * (1 - yardOut),
          fontFamily: 'IBM Plex Mono, monospace', fontSize: 13, fontWeight: 600,
          letterSpacing: '.16em', textTransform: 'uppercase', color: gateHot > 0.5 ? RED : INK,
        },
      }, 'the gate · one decision each'),

      rail('release', OUT.release.y - 34, COUNTS.release, 'release'),
      rail('quarantine / retest', OUT.quarantine.y - 34, COUNTS.quarantine, 'quarantine'),
      rail('destroy', OUT.destroy.y - 34, COUNTS.destroy, 'destroy'),

      // the bar's frame, drawn as the trucks arrive in it
      React.createElement('div', {
        style: {
          position: 'absolute', left: BAR.x - 3, top: BAR.y - 3, width: BAR.w + 6, height: BAR.h + 6,
          border: '3px solid ' + INK, opacity: barIn,
        },
      }),
      marks
    ),

    // ---- fixed HUD, outside the camera ----
    React.createElement('div', {
      style: { position: 'absolute', left: 72, top: 60, display: 'flex', flexDirection: 'column', gap: 6 },
    },
      React.createElement('div', {
        style: {
          fontFamily: 'IBM Plex Mono, monospace', fontSize: 15, letterSpacing: '.2em',
          textTransform: 'uppercase', color: N700,
        },
      }, 'ColdCall · the whole corpus, at once'),
      React.createElement('div', {
        style: { fontSize: 52, fontWeight: 800, letterSpacing: '-.025em', lineHeight: 1.05, maxWidth: 980 },
      }, '206 real shipment legs. 206 real decisions.')
    ),

    React.createElement('div', {
      style: {
        position: 'absolute', right: 72, top: 62, textAlign: 'right',
        fontFamily: 'IBM Plex Mono, monospace', fontVariantNumeric: 'tabular-nums',
      },
    },
      React.createElement('div', { style: { fontSize: 13, letterSpacing: '.16em', textTransform: 'uppercase', color: N700 } }, 'decided'),
      React.createElement('div', { style: { fontSize: 46, fontWeight: 600, letterSpacing: '-.03em', lineHeight: 1.05 } }, landed + ' / 206'),
      React.createElement('div', { style: { fontSize: 13, letterSpacing: '.14em', textTransform: 'uppercase', color: N700, marginTop: 4 } }, 'cross-check disagreements 0')
    ),

    // ---- the read-out under the bar, once it has formed ----
    React.createElement('div', {
      style: {
        position: 'absolute', left: BAR.x, top: BAR.y + BAR.h + 34, display: 'flex', gap: 54,
        opacity: MOTION.enter(CUES.Hold - 0.6, CUES.Hold + 0.4),
      },
    },
      [['release', COUNTS.release, GROUND], ['quarantine / retest', COUNTS.quarantine, HATCH], ['destroy', COUNTS.destroy, RED]]
        .map(([label, n, bg], i) => React.createElement('div', { key: i, style: { display: 'flex', alignItems: 'center', gap: 14 } },
          React.createElement('div', { style: { width: 42, height: 20, background: bg, border: bg === RED ? 'none' : '2px solid ' + INK } }),
          React.createElement('div', { style: { fontFamily: 'IBM Plex Mono, monospace', fontSize: 34, fontWeight: 600, letterSpacing: '-.02em', fontVariantNumeric: 'tabular-nums' } }, n),
          React.createElement('div', { style: { fontSize: 17, color: N700 } }, label)
        ))
    ),

    React.createElement(Captions, {
      items: [
        { at: 0.2, text: 'One shipment leg. Amoxicillin 500 mg, Rotterdam to Lyon.' },
        { at: 2.6, text: 'On the road it reached 27.0 °C against a 20–25 °C label.' },
        { at: CUES.Windshield + 0.6, text: '232 of 1,233 recorded minutes were out of range.' },
        { at: CUES.Lane + 0.3, text: 'It is one of 48 legs in a real pharma logger dataset.' },
        { at: CUES.Fleet + 0.4, text: 'Five public datasets. 206 legs. Every one scored on its own recorded telemetry.' },
        { at: CUES.Sweep + 0.5, text: 'Each leg runs the same deterministic math and arrives at one gate. None of them is coloured yet.' },
        { at: CUES.Sweep + 2.5, text: 'The verdict is painted at the gate — release, hold, or destroy.' },
        { at: CUES.Gate + 1.2, text: 'Five lanes in. Three tracks out.' },
        { at: CUES.Resolve + 0.4, text: 'Every truck you just watched is one segment of this bar.' },
        { at: CUES.Hold + 0.5, until: 99, text: '13 release · 23 quarantine · 170 destroy — and a second implementation agreed on all 206.' },
      ],
      style: { bottom: 54, left: 72, right: 72, fontSize: 26 },
    })
  );
}

function FleetTweaks() {
  const { useTweaks, TweaksPanel, TweakSection, TweakToggle } = window;
  const [t, setTweak] = useTweaks(window.TWEAK_DEFAULTS || { motionEditor: true });
  return React.createElement(TweaksPanel, null,
    React.createElement(TweakSection, { label: 'Timeline' }),
    React.createElement(TweakToggle, {
      label: 'Motion editor', value: t.motionEditor,
      onChange: v => setTweak('motionEditor', v),
    })
  );
}

window.FleetSweep = FleetSweep;
window.FleetTweaks = FleetTweaks;
