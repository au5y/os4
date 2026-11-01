(function () {
  "use strict";
  const U = OS4.util;
  const el = U.el;
  U.header("task3.html");

  const caseKeys = Object.keys(OS4).filter((k) => k.startsWith("task3_")).sort();
  if (!caseKeys.length) return;
  const LEAD = ["fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "battery", "fleet_cost_usd", "mau", "mau_os3a_extended"];
  const HIDE = ["road_chassis", "bike_frame"];
  const TYPE_ORDER = { "road-only": 0, "bike-only": 1, mixed: 2 };

  // ---------- per-case data ----------
  const cases = {};
  for (const key of caseKeys) {
    const P = OS4[key];
    const C = U.Columnar(P.table);
    const n = C.n;
    const logCost = new Float64Array(n);
    const type = new Uint8Array(n);
    const typeDict = C.dict("fleet_type");
    const typeRaw = P.table.data.fleet_type;
    const costRaw = P.table.data.fleet_cost_usd;
    for (let i = 0; i < n; i++) {
      logCost[i] = Math.log10(Math.max(costRaw[i], 1));
      type[i] = TYPE_ORDER[typeDict[typeRaw[i]]] ?? 2;
    }
    const onFront = {};
    for (const [u, idx] of Object.entries(P.fronts)) onFront[u] = new Set(idx);
    cases[key] = { key, P, C, n, logCost, type, onFront, ids: null };
  }
  function idIndex(c) {
    if (!c.ids) {
      c.ids = new Map();
      for (let i = 0; i < c.n; i++) c.ids.set(rowId(c, i), i);
    }
    return c.ids;
  }
  const rowId = (c, i) => U.archId({ n_road: c.C.get(i, "n_road"), road_variant: c.C.get(i, "road_variant"), n_bike: c.C.get(i, "n_bike"), bike_variant: c.C.get(i, "bike_variant") });

  // ---------- state ----------
  const state = {
    key: caseKeys.includes("task3_removable") ? "task3_removable" : caseKeys[0],
    utility: "mau",
    colorBy: "type",
    view: null, // {x0, x1 (log10 $), y0, y1}
    pinned: null,
    hover: null,
    filtered: new Int32Array(0),
    f: { types: new Set(U.TYPES), road_chassis: "", bike_frame: "", battery: "", n_road: [null, null], n_bike: [null, null], cost: [null, null], minU: null, flags: new Set() },
  };
  const cur = () => cases[state.key];

  // ---------- toolbar ----------
  const caseToggle = document.getElementById("case-toggle");
  for (const key of caseKeys) {
    const input = el("input", { type: "radio", name: "case", value: key, checked: key === state.key ? true : null });
    input.addEventListener("change", () => setCase(key));
    caseToggle.appendChild(el("label", { title: OS4[key].label }, [input, key.replace("task3_", "") + " batteries"]));
  }
  const utilSel = document.getElementById("utility");
  const colorSel = document.getElementById("color-by");
  colorSel.addEventListener("change", () => {
    state.colorBy = colorSel.value;
    legend();
    draw();
  });
  utilSel.addEventListener("change", () => {
    state.utility = utilSel.value;
    state.view = null;
    applyFilters();
  });
  document.getElementById("reset-view").addEventListener("click", () => {
    state.view = null;
    draw();
  });

  function fillUtilities() {
    const c = cur();
    const prev = state.utility;
    utilSel.textContent = "";
    for (const u of c.P.utilities) utilSel.appendChild(el("option", { value: u, text: U.label(u) }));
    state.utility = c.P.utilities.includes(prev) ? prev : c.P.utilities[0];
    utilSel.value = state.utility;
  }

  // ---------- filters ----------
  const fbox = document.getElementById("filters");
  const filterEls = {};
  function numInput(placeholder, onchange, step) {
    const i = el("input", { type: "number", placeholder, step: step || "any", min: "0" });
    i.addEventListener("input", () => onchange(i.value === "" ? null : +i.value));
    return i;
  }
  function buildFilters() {
    const c = cur();
    const C = c.C;
    fbox.textContent = "";
    // fleet type
    const types = el("div", { class: "f" }, [el("span", { text: "fleet type" })]);
    const row = el("div", { class: "range" });
    for (const t of U.TYPES) {
      const cb = el("input", { type: "checkbox", checked: state.f.types.has(t) ? true : null });
      cb.addEventListener("change", () => {
        cb.checked ? state.f.types.add(t) : state.f.types.delete(t);
        applyFilters();
      });
      row.appendChild(el("label", { class: "chk" }, [cb, U.shapeSvg(U.typeShape(t), U.typeColor(t), 11), t]));
    }
    types.appendChild(row);
    fbox.appendChild(types);
    // categorical selects
    for (const [key, label] of [["road_chassis", "road chassis"], ["bike_frame", "bike frame"], ["battery", "bike battery"]]) {
      if (!C.has(key)) continue;
      const s = el("select", null, [el("option", { value: "", text: "any" })].concat(C.dict(key).map((v) => el("option", { value: v, text: v }))));
      if (!C.dict(key).includes(state.f[key])) state.f[key] = "";
      s.value = state.f[key];
      s.addEventListener("change", () => {
        state.f[key] = s.value;
        applyFilters();
      });
      fbox.appendChild(el("label", { class: "f" }, [el("span", { text: label }), s]));
    }
    // ranges
    const range = (name, label, key, step, scale) => {
      const lo = numInput("min", (v) => { state.f[key][0] = v === null ? null : v * (scale || 1); applyFilters(); }, step);
      const hi = numInput("max", (v) => { state.f[key][1] = v === null ? null : v * (scale || 1); applyFilters(); }, step);
      if (state.f[key][0] !== null) lo.value = state.f[key][0] / (scale || 1);
      if (state.f[key][1] !== null) hi.value = state.f[key][1] / (scale || 1);
      filterEls[key] = [lo, hi];
      fbox.appendChild(el("div", { class: "f" }, [el("span", { text: label }), el("div", { class: "range" }, [lo, "–", hi])]));
    };
    range("nr", "N road", "n_road", "5");
    range("nb", "N bike", "n_bike", "25");
    range("cost", "cost ($M)", "cost", "0.1", 1e6);
    const minU = numInput("e.g. 0.9", (v) => { state.f.minU = v; applyFilters(); }, "0.01");
    minU.max = "1";
    if (state.f.minU !== null) minU.value = state.f.minU;
    fbox.appendChild(el("label", { class: "f" }, [el("span", { text: "min utility" }), minU]));
    // boolean flags: every bool column in the data
    const flags = el("div", { class: "f" }, [el("span", { text: "only architectures meeting" })]);
    const frow = el("div", { class: "range" });
    for (const col of C.columns.filter((c) => c.kind === "bool")) {
      const cb = el("input", { type: "checkbox", checked: state.f.flags.has(col.name) ? true : null });
      cb.addEventListener("change", () => {
        cb.checked ? state.f.flags.add(col.name) : state.f.flags.delete(col.name);
        applyFilters();
      });
      frow.appendChild(el("label", { class: "chk", title: col.name }, [cb, col.label.replace(/^meets /, "")]));
    }
    flags.appendChild(frow);
    fbox.appendChild(flags);
    const reset = el("button", { type: "button", text: "Reset filters" });
    reset.addEventListener("click", () => {
      state.f = { types: new Set(U.TYPES), road_chassis: "", bike_frame: "", battery: "", n_road: [null, null], n_bike: [null, null], cost: [null, null], minU: null, flags: new Set() };
      buildFilters();
      applyFilters();
    });
    fbox.appendChild(el("div", { class: "f" }, [el("span", { text: " " }), reset]));
  }
  function filtersActive() {
    const f = state.f;
    return (
      f.types.size < 3 || f.road_chassis || f.bike_frame || f.battery || f.flags.size || f.minU !== null ||
      [f.n_road, f.n_bike, f.cost].some((r) => r[0] !== null || r[1] !== null)
    );
  }

  let pending = false;
  function applyFilters() {
    if (pending) return;
    pending = true;
    requestAnimationFrame(() => {
      pending = false;
      const c = cur();
      const C = c.C;
      const f = state.f;
      const d = c.P.table.data;
      const catIdx = (key) => (f[key] && C.has(key) ? C.dict(key).indexOf(f[key]) : null);
      const rc = catIdx("road_chassis"), bf = catIdx("bike_frame"), bt = catIdx("battery");
      const typeOk = [0, 1, 2].map((t) => f.types.has(U.TYPES[t]));
      const util = d[state.utility];
      const flagCols = [...f.flags].filter((k) => d[k]).map((k) => d[k]);
      const inRange = (v, r) => (r[0] === null || v >= r[0]) && (r[1] === null || v <= r[1]);
      const out = [];
      for (let i = 0; i < c.n; i++) {
        if (!typeOk[c.type[i]]) continue;
        if (rc !== null && d.road_chassis[i] !== rc) continue;
        if (bf !== null && d.bike_frame[i] !== bf) continue;
        if (bt !== null && d.battery[i] !== bt) continue;
        if (!inRange(d.n_road[i], f.n_road) || !inRange(d.n_bike[i], f.n_bike) || !inRange(d.fleet_cost_usd[i], f.cost)) continue;
        if (f.minU !== null && !(util[i] >= f.minU)) continue;
        let ok = true;
        for (const col of flagCols) if (col[i] !== 1) { ok = false; break; }
        if (ok) out.push(i);
      }
      state.filtered = Int32Array.from(out);
      filteredFront = filtersActive() ? frontOf(out) : null;
      counts();
      legend();
      draw();
      table.update();
    });
  }
  let filteredFront = null;
  function frontOf(idx) {
    const c = cur();
    const d = c.P.table.data;
    const util = d[state.utility];
    const sorted = idx.slice().sort((a, b) => d.fleet_cost_usd[a] - d.fleet_cost_usd[b] || util[b] - util[a]);
    const front = [];
    let best = -Infinity;
    for (const i of sorted) if (util[i] > best) { best = util[i]; front.push(i); }
    return front;
  }

  function counts() {
    const c = cur();
    const P = c.P;
    const t = P.totals, s = P.shown;
    const box = document.getElementById("counts");
    box.textContent =
      "Showing " + state.filtered.length.toLocaleString() + " of " + s.all.toLocaleString() + " points loaded; the full tradespace for this case has " +
      t.all.toLocaleString() + " architectures (" + U.TYPES.map((k) => (t[k] || 0).toLocaleString() + " " + k).join(", ") + "). " +
      "All road-only, bike-only and front points are loaded; mixed fleets are a sample of " + (s.mixed || 0).toLocaleString() + " of " + (t.mixed || 0).toLocaleString() + ". " +
      (t.screened_out ? t.screened_out.toLocaleString() + " grid points missed a Table 1 threshold and are not in the tradespace." : "");
    box.title = P.sampling;
  }

  // ---------- chart ----------
  const box = document.getElementById("canvas-box");
  const canvas = document.getElementById("chart");
  const ctx = canvas.getContext("2d");
  const tip = document.getElementById("tooltip");
  const M = { l: 58, r: 18, t: 14, b: 44 };
  let W = 0, H = 0;
  function resize() {
    const r = box.getBoundingClientRect();
    const dpr = window.devicePixelRatio || 1;
    W = r.width;
    H = r.height;
    canvas.width = Math.round(W * dpr);
    canvas.height = Math.round(H * dpr);
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    draw();
  }
  function defaultView() {
    const c = cur();
    const u = c.P.table.data[state.utility];
    let x0 = Infinity, x1 = -Infinity, y0 = Infinity, y1 = -Infinity;
    for (let i = 0; i < c.n; i++) {
      if (c.logCost[i] < x0) x0 = c.logCost[i];
      if (c.logCost[i] > x1) x1 = c.logCost[i];
      if (u[i] !== null && u[i] < y0) y0 = u[i];
      if (u[i] !== null && u[i] > y1) y1 = u[i];
    }
    const px = (x1 - x0) * 0.04 || 0.1, py = (y1 - y0) * 0.05 || 0.02;
    return { x0: x0 - px, x1: x1 + px, y0: Math.max(0, y0 - py), y1: Math.min(1.02, y1 + py) };
  }
  const view = () => state.view || (state.view = defaultView());
  const sx = (lc) => { const v = view(); return M.l + ((lc - v.x0) / (v.x1 - v.x0)) * (W - M.l - M.r); };
  const sy = (u) => { const v = view(); return M.t + ((v.y1 - u) / (v.y1 - v.y0)) * (H - M.t - M.b); };
  const invX = (px) => { const v = view(); return v.x0 + ((px - M.l) / (W - M.l - M.r)) * (v.x1 - v.x0); };
  const invY = (py) => { const v = view(); return v.y1 - ((py - M.t) / (H - M.t - M.b)) * (v.y1 - v.y0); };

  function sizeMeasure(c, i) {
    const d = c.P.table.data;
    if (state.colorBy === "n_road") return d.n_road[i];
    if (state.colorBy === "n_bike") return d.n_bike[i];
    return d.n_road[i] + d.n_bike[i];
  }
  function sizeDomain(c) {
    let lo = Infinity, hi = -Infinity;
    for (let i = 0; i < c.n; i++) {
      const v = sizeMeasure(c, i);
      if (v > 0) { lo = Math.min(lo, v); hi = Math.max(hi, v); }
    }
    return [lo, hi];
  }
  function binOf(v, dom) {
    if (!(v > 0)) return -1;
    if (dom[1] === dom[0]) return 9;
    return Math.min(9, Math.max(0, Math.floor(((v - dom[0]) / (dom[1] - dom[0])) * 10)));
  }

  function shapePath(shape, x, y, r) {
    if (shape === 0) { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2); }
    else if (shape === 1) { const h = r * 1.25; ctx.moveTo(x, y - h); ctx.lineTo(x + h, y + h * 0.8); ctx.lineTo(x - h, y + h * 0.8); ctx.closePath(); }
    else { const h = r * 0.9; ctx.rect(x - h, y - h, 2 * h, 2 * h); }
  }
  function logTicks(x0, x1, width) {
    const out = [];
    const maxTicks = Math.max(2, Math.floor(width / 64));
    for (const mults of [[1, 2, 5], [1, 3], [1]]) {
      out.length = 0;
      for (let e = Math.floor(x0) - 1; e <= Math.ceil(x1); e++) for (const m of mults) {
        const lc = e + Math.log10(m);
        if (lc >= x0 && lc <= x1) out.push(lc);
      }
      if (out.length <= maxTicks) break;
    }
    return out.slice();
  }
  function linTicks(lo, hi, n) {
    const step0 = (hi - lo) / n;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0);
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + 1e-12; v += step) out.push(+v.toFixed(6));
    return out;
  }

  function draw() {
    if (!W) return;
    const c = cur();
    const d = c.P.table.data;
    const util = d[state.utility];
    const v = view();
    const col = { ink: U.css("--ink"), ink2: U.css("--ink-2"), muted: U.css("--muted"), grid: U.css("--grid"), axis: U.css("--axis"), surface: U.css("--surface"), star: U.css("--star") };
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = col.surface;
    ctx.fillRect(0, 0, W, H);
    ctx.font = "11px " + U.css("--font");
    // grid + ticks
    ctx.lineWidth = 1;
    ctx.strokeStyle = col.grid;
    ctx.fillStyle = col.muted;
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    for (const t of linTicks(v.y0, v.y1, Math.max(3, Math.floor((H - M.t - M.b) / 60)))) {
      const y = Math.round(sy(t)) + 0.5;
      ctx.beginPath(); ctx.moveTo(M.l, y); ctx.lineTo(W - M.r, y); ctx.stroke();
      ctx.fillText(t.toFixed(t * 100 % 1 ? 3 : 2), M.l - 6, y);
    }
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    for (const t of logTicks(v.x0, v.x1, W - M.l - M.r)) {
      const x = Math.round(sx(t)) + 0.5;
      ctx.beginPath(); ctx.moveTo(x, M.t); ctx.lineTo(x, H - M.b); ctx.stroke();
      ctx.fillText(U.moneyShort(Math.pow(10, t)), x, H - M.b + 6);
    }
    ctx.strokeStyle = col.axis;
    ctx.beginPath(); ctx.moveTo(M.l, H - M.b + 0.5); ctx.lineTo(W - M.r, H - M.b + 0.5); ctx.stroke();
    ctx.fillStyle = col.ink2;
    ctx.fillText("fleet cost (vehicle capital cost, log scale)", (M.l + W - M.r) / 2, H - 18);
    ctx.save();
    ctx.translate(14, (M.t + H - M.b) / 2);
    ctx.rotate(-Math.PI / 2);
    ctx.textBaseline = "middle";
    ctx.fillText(U.label(state.utility), 0, 0);
    ctx.restore();

    // plot area clip
    ctx.save();
    ctx.beginPath();
    ctx.rect(M.l, M.t, W - M.l - M.r, H - M.t - M.b);
    ctx.clip();

    // points: mixed first, then road-only, then bike-only
    const F = state.filtered;
    const byType = state.colorBy === "type";
    const dom = byType ? null : sizeDomain(c);
    const ramp = U.ramp();
    const typeColors = U.TYPES.map((t) => U.typeColor(t));
    for (const t of [2, 0, 1]) {
      const r = t === 2 ? 2.6 : 3.4;
      ctx.globalAlpha = t === 2 ? 0.4 : 0.85;
      if (byType) {
        ctx.fillStyle = typeColors[t];
        ctx.beginPath();
        for (let k = 0; k < F.length; k++) {
          const i = F[k];
          if (c.type[i] !== t || util[i] === null) continue;
          shapePath(t, sx(c.logCost[i]), sy(util[i]), r);
        }
        ctx.fill();
      } else {
        // one path per ramp bin (and one for "none")
        const paths = Array.from({ length: 11 }, () => new Path2D());
        for (let k = 0; k < F.length; k++) {
          const i = F[k];
          if (c.type[i] !== t || util[i] === null) continue;
          const b = binOf(sizeMeasure(c, i), dom);
          const p = paths[b + 1];
          const x = sx(c.logCost[i]), y = sy(util[i]);
          if (t === 0) { p.moveTo(x + r, y); p.arc(x, y, r, 0, Math.PI * 2); }
          else if (t === 1) { const h = r * 1.25; p.moveTo(x, y - h); p.lineTo(x + h, y + h * 0.8); p.lineTo(x - h, y + h * 0.8); p.closePath(); }
          else { const h = r * 0.9; p.rect(x - h, y - h, 2 * h, 2 * h); }
        }
        paths.forEach((p, b) => { ctx.fillStyle = b === 0 ? col.muted : ramp[b - 1]; ctx.fill(p); });
      }
    }
    ctx.globalAlpha = 1;

    // Pareto front (all architectures of this case) and front of the filtered points
    const step = (idx, color, width, alpha) => {
      if (!idx || !idx.length) return;
      ctx.strokeStyle = color;
      ctx.lineWidth = width;
      ctx.globalAlpha = alpha;
      ctx.lineJoin = "round";
      ctx.beginPath();
      idx.forEach((i, k) => {
        const x = sx(c.logCost[i]), y = sy(util[i]);
        if (k === 0) ctx.moveTo(x, y);
        else { ctx.lineTo(x, sy(util[idx[k - 1]])); ctx.lineTo(x, y); }
      });
      ctx.lineTo(W, sy(util[idx[idx.length - 1]]));
      ctx.stroke();
      ctx.globalAlpha = 1;
    };
    step(c.P.fronts[state.utility], col.ink, 2, 0.6);
    if (filteredFront) step(filteredFront, col.star, 2, 0.9);

    // Task 2 reference architectures
    const archs = (OS4.task2 && OS4.task2.architectures) || [];
    ctx.lineWidth = 1.5;
    ctx.strokeStyle = col.ink;
    ctx.fillStyle = col.ink;
    ctx.textAlign = "left";
    ctx.textBaseline = "bottom";
    ctx.font = "600 11px " + U.css("--font");
    archs.forEach((a, k) => {
      if (a[state.utility] === null || a[state.utility] === undefined || !a.fleet_cost_usd) return;
      const x = sx(Math.log10(a.fleet_cost_usd)), y = sy(a[state.utility]);
      ctx.beginPath(); ctx.arc(x, y, 6, 0, Math.PI * 2); ctx.stroke();
      ctx.fillText(String(a.architecture).split(" ")[0] || String(k + 1), x + 7, y - 4);
    });

    // selected (starred) architectures in this case
    const sel = OS4.selection.all();
    const ids = Object.keys(sel);
    if (ids.length) {
      const map = idIndex(c);
      ctx.strokeStyle = col.star;
      ctx.lineWidth = 2;
      for (const id of ids) {
        const i = map.get(id);
        if (i === undefined) continue;
        ctx.beginPath(); ctx.arc(sx(c.logCost[i]), sy(util[i]), 7, 0, Math.PI * 2); ctx.stroke();
      }
    }

    // utopia point
    const up = c.P.utopia[state.utility];
    if (up) {
      const x = sx(Math.log10(up[0])), y = sy(up[1]);
      ctx.fillStyle = col.ink;
      ctx.strokeStyle = col.surface;
      ctx.lineWidth = 2;
      ctx.beginPath();
      for (let k = 0; k < 10; k++) {
        const rad = k % 2 ? 3.6 : 8.5, a = -Math.PI / 2 + (k * Math.PI) / 5;
        k ? ctx.lineTo(x + rad * Math.cos(a), y + rad * Math.sin(a)) : ctx.moveTo(x + rad * Math.cos(a), y + rad * Math.sin(a));
      }
      ctx.closePath(); ctx.stroke(); ctx.fill();
      ctx.font = "11px " + U.css("--font");
      ctx.textBaseline = "middle";
      ctx.fillText("utopia", x + 11, y);
    }

    // hover + pinned
    for (const [i, r, w] of [[state.hover, 6, 1.5], [state.pinned, 9, 2.5]]) {
      if (i === null || util[i] === null) continue;
      ctx.strokeStyle = col.ink;
      ctx.lineWidth = w;
      ctx.beginPath(); ctx.arc(sx(c.logCost[i]), sy(util[i]), r, 0, Math.PI * 2); ctx.stroke();
    }
    ctx.restore();
  }

  // ---------- legend ----------
  function legend() {
    const L = document.getElementById("legend");
    L.textContent = "";
    if (state.colorBy === "type") {
      for (const t of U.TYPES) L.appendChild(U.legendItem(U.shapeSvg(U.typeShape(t), U.typeColor(t)), t));
    } else {
      const dom = sizeDomain(cur());
      const ramp = U.ramp();
      const name = { n_road: "N road", n_bike: "N bike", total: "N road + N bike" }[state.colorBy];
      const bar = el("span", { class: "ramp", "aria-hidden": "true" }, ramp.map((c) => el("span", { style: "background:" + c })));
      L.appendChild(el("span", { class: "item" }, [name + ": " + (isFinite(dom[0]) ? dom[0] : "–"), bar, isFinite(dom[1]) ? String(dom[1]) : "–"]));
      L.appendChild(U.legendItem(U.shapeSvg("circle", U.css("--muted")), "none (0)"));
      for (const t of U.TYPES) L.appendChild(U.legendItem(U.shapeSvg(U.typeShape(t), U.css("--ink-2")), t));
    }
    L.appendChild(U.legendItem(U.shapeSvg("line", U.css("--ink")), "Pareto front (all architectures)"));
    if (filtersActive()) L.appendChild(U.legendItem(U.shapeSvg("line", U.css("--star")), "front of filtered points"));
    L.appendChild(U.legendItem(U.shapeSvg("star", U.css("--ink")), "utopia point"));
    L.appendChild(U.legendItem(U.shapeSvg("ring", U.css("--ink")), "Task 2 architectures 1–5"));
    L.appendChild(U.legendItem(U.shapeSvg("ring", U.css("--star")), "your selection"));
  }

  // ---------- hover / pin / zoom / pan ----------
  function nearest(px, py, maxDist) {
    const c = cur();
    const util = c.P.table.data[state.utility];
    const F = state.filtered;
    let best = null, bd = maxDist * maxDist;
    for (let k = 0; k < F.length; k++) {
      const i = F[k];
      if (util[i] === null) continue;
      const dx = sx(c.logCost[i]) - px, dy = sy(util[i]) - py;
      const dd = dx * dx + dy * dy;
      if (dd < bd) { bd = dd; best = i; }
    }
    return best;
  }
  const local = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  let drag = null;
  canvas.addEventListener("pointerdown", (e) => {
    const [x, y] = local(e);
    drag = { x, y, v: Object.assign({}, view()), moved: false };
    canvas.setPointerCapture(e.pointerId);
  });
  canvas.addEventListener("pointermove", (e) => {
    const [x, y] = local(e);
    if (drag) {
      const dx = x - drag.x, dy = y - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
      if (drag.moved) {
        canvas.classList.add("dragging");
        const v = drag.v;
        const kx = (v.x1 - v.x0) / (W - M.l - M.r), ky = (v.y1 - v.y0) / (H - M.t - M.b);
        state.view = { x0: v.x0 - dx * kx, x1: v.x1 - dx * kx, y0: v.y0 + dy * ky, y1: v.y1 + dy * ky };
        hideTip();
        draw();
        return;
      }
    }
    const i = nearest(x, y, 16);
    if (i !== state.hover) {
      state.hover = i;
      draw();
    }
    i === null ? hideTip() : showTip(i, x, y);
  });
  canvas.addEventListener("pointerup", (e) => {
    canvas.classList.remove("dragging");
    if (drag && !drag.moved) {
      const [x, y] = local(e);
      pin(nearest(x, y, 16), true);
    }
    drag = null;
  });
  canvas.addEventListener("pointerleave", () => {
    state.hover = null;
    hideTip();
    draw();
  });
  canvas.addEventListener("dblclick", () => {
    state.view = null;
    draw();
  });
  canvas.addEventListener(
    "wheel",
    (e) => {
      e.preventDefault();
      const [x, y] = local(e);
      const k = Math.exp(Math.max(-0.5, Math.min(0.5, e.deltaY * 0.0015)));
      const v = view();
      const cx = invX(x), cy = invY(y);
      state.view = { x0: cx - (cx - v.x0) * k, x1: cx + (v.x1 - cx) * k, y0: cy - (cy - v.y0) * k, y1: cy + (v.y1 - cy) * k };
      hideTip();
      draw();
    },
    { passive: false }
  );

  const TIP_KEYS = ["fleet_type", "fleet_capacity_per_h", "passenger_volume", "wait_time", "availability", "travel_time", "bike_share"];
  function showTip(i, x, y) {
    const c = cur();
    const C = c.C;
    tip.textContent = "";
    tip.appendChild(el("div", { class: "t", text: rowId(c, i) }));
    const row = (label, value) => tip.appendChild(el("div", { class: "row" }, [el("span", { text: label }), el("span", { class: "v", text: value })]));
    row("fleet cost", U.money(C.get(i, "fleet_cost_usd")));
    for (const u of c.P.utilities) row(U.label(u), U.fmt(u, C.get(i, u)));
    for (const k of TIP_KEYS) if (C.has(k)) row(U.label(k), U.fmt(k, C.get(i, k)));
    if (c.onFront[state.utility] && c.onFront[state.utility].has(i)) row("Pareto front", "yes");
    tip.appendChild(el("div", { class: "muted small", text: "click to pin" }));
    tip.hidden = false;
    const tw = tip.offsetWidth, th = tip.offsetHeight;
    tip.style.left = (x + 14 + tw > W ? x - tw - 14 : x + 14) + "px";
    tip.style.top = Math.max(0, Math.min(H - th, y - th / 2)) + "px";
  }
  function hideTip() {
    tip.hidden = true;
  }

  // ---------- details panel ----------
  const details = document.getElementById("details");
  function renderDetails() {
    details.textContent = "";
    const c = cur();
    const i = state.pinned;
    if (i === null) {
      details.append(
        el("h3", { text: "Details" }),
        el("p", { class: "muted", text: "Click a point (or a table row) to pin its details here. ☆ adds it to your selection, which you can export from the Selected page." }),
        el("p", { class: "muted small", text: c.P.label })
      );
      return;
    }
    const id = rowId(c, i);
    const head = el("h3", null, [U.starButton(id, () => record(i), "Task 3 (" + c.key.replace("task3_", "") + " batteries)"), " ", id]);
    const dl = el("dl");
    const front = Object.entries(c.onFront).filter(([, s]) => s.has(i)).map(([u]) => U.label(u));
    dl.append(el("dt", { text: "case" }), el("dd", { text: c.key.replace("task3_", "") + " batteries" }));
    dl.append(el("dt", { text: "on Pareto front" }), el("dd", { text: front.length ? front.join(", ") : "no" }));
    for (const k of orderedNames(c)) {
      dl.append(el("dt", { text: U.label(k) }), el("dd", { text: U.fmt(k, c.C.get(i, k)) }));
    }
    const unpin = el("button", { type: "button", text: "Unpin" });
    unpin.addEventListener("click", () => pin(null));
    details.append(head, dl, el("p", null, [unpin]));
  }
  function record(i) {
    const c = cur();
    return Object.assign({ case: c.key.replace("task3_", "") }, c.C.record(i));
  }
  function pin(i, fromChart) {
    state.pinned = i;
    renderDetails();
    draw();
    if (fromChart && i !== null) table.setActive(i);
  }
  OS4.selection.onChange(() => {
    draw();
    if (state.pinned !== null) renderDetails();
  });

  // ---------- table ----------
  function orderedNames(c) {
    const names = c.C.names.filter((n) => !HIDE.includes(n));
    return LEAD.filter((k) => names.includes(k)).concat(names.filter((k) => !LEAD.includes(k)));
  }
  const table = U.Table(document.getElementById("table"), {
    columns: [],
    getValue: (i, k) => cur().C.get(i, k),
    rows: () => Array.from(state.filtered),
    id: (i) => rowId(cur(), i),
    record: (i) => record(i),
    source: "Task 3",
    sort: { key: "fleet_cost_usd", dir: 1 },
    onRowClick: (i) => {
      pin(i);
      table.setActive(i);
    },
    pageSize: 50,
    note: () => "filtered from the loaded points; sort by clicking a header",
  });
  // ---------- case switching ----------
  function setCase(key) {
    state.key = key;
    state.pinned = null;
    state.hover = null;
    state.view = null;
    fillUtilities();
    buildFilters();
    table.setColumns(U.columnsFor(orderedNames(cur())));
    legend();
    renderDetails();
    applyFilters();
  }
  new ResizeObserver(resize).observe(box);
  U.onTheme(() => {
    legend();
    draw();
  });
  setCase(state.key);
  U.footer();
})();
