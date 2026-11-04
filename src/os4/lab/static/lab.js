/* OS4 Model Lab: build a config from presets and inputs, run it on the lab server, save/export/compare runs. */
(function () {
  "use strict";
  const U = OS4.util;
  const $ = (id) => document.getElementById(id);
  const PLAN = "https://au5y.github.io/os4/plan.html#q";
  const STORE = { current: "os4lab.current", configs: "os4lab.configs", runs: "os4lab.runs" };
  const MAX_RUNS = 40;
  const KNEE = 0.94;

  const state = { schema: null, presets: [], base: null, config: null, presetId: null, result: null, zoom: true, compare: [] };

  // ---------- storage (every access guarded: private windows and full quotas must not break the page) ----------
  function load(key, fallback) {
    try {
      const v = localStorage.getItem(key);
      return v ? JSON.parse(v) : fallback;
    } catch (e) {
      return fallback;
    }
  }
  function store(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      return false;
    }
  }
  const clone = (o) => JSON.parse(JSON.stringify(o));
  const same = (a, b) => JSON.stringify(a) === JSON.stringify(b);

  function download(name, obj) {
    const blob = new Blob([JSON.stringify(obj, null, 2)], { type: "application/json" });
    const a = U.el("a", { href: URL.createObjectURL(blob), download: name });
    document.body.appendChild(a);
    a.click();
    setTimeout(() => (URL.revokeObjectURL(a.href), a.remove()), 0);
  }
  const slug = (s) => (s || "os4-lab").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  // ---------- API ----------
  async function api(path, body) {
    const res = await fetch(path, body ? { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) } : {});
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  // ---------- form ----------
  const S = () => state.config.scenario;
  const baseS = () => (state.base ? state.base.scenario : {});

  function setDirty() {
    store(STORE.current, { config: state.config, presetId: state.presetId });
    renderForm();
    if ($("auto").checked) scheduleCalc();
  }

  function field(f) {
    const v = S()[f.key];
    const changed = !same(v, baseS()[f.key]);
    const label = U.el("span", { class: "lab-label" }, [f.label, f.q ? U.el("a", { href: PLAN + f.q, target: "_blank", rel: "noopener", text: "Q" + f.q, title: "PLAN.md Q" + f.q }) : null]);
    const box = U.el("span", { class: "lab-input" });
    const num = (val, on) =>
      U.el("input", {
        type: "number", value: typeof val === "number" ? +val.toFixed(3) : val ?? "", min: f.min, max: f.max, step: f.step || "any", "aria-label": f.label,
        onchange: (e) => {
          const x = e.target.value === "" ? null : Number(e.target.value);
          on(x);
        },
      });
    if (f.kind === "num") {
      box.append(num(v, (x) => { S()[f.key] = x ?? baseS()[f.key]; setDirty(); }), U.el("span", { class: "unit", text: f.unit || "" }));
    } else if (f.kind === "opt") {
      const on = v !== null && v !== undefined;
      const cb = U.el("input", {
        type: "checkbox", checked: on, title: on ? "on" : f.off, "aria-label": f.label + " on",
        onchange: (e) => {
          S()[f.key] = e.target.checked ? (baseS()[f.key] ?? f.min) : null;
          setDirty();
        },
      });
      box.append(cb);
      if (on) box.append(num(v, (x) => { S()[f.key] = x; setDirty(); }), U.el("span", { class: "unit", text: f.unit || "" }));
      else box.append(U.el("span", { class: "muted small", text: f.off }));
    } else if (f.kind === "list") {
      box.append(U.el("input", {
        type: "text", value: (v || []).join(", "), "aria-label": f.label,
        onchange: (e) => {
          S()[f.key] = e.target.value.split(/[,\s]+/).filter(Boolean).map(Number).filter((x) => !Number.isNaN(x));
          setDirty();
        },
      }));
    } else if (f.kind === "autonomy") {
      for (const lvl of ["A3", "A4", "A5"]) {
        box.append(U.el("label", { class: "small" }, [U.el("input", {
          type: "checkbox", checked: v.includes(lvl),
          onchange: (e) => {
            const set = new Set(S()[f.key]);
            e.target.checked ? set.add(lvl) : set.delete(lvl);
            if (set.size) S()[f.key] = ["A3", "A4", "A5"].filter((x) => set.has(x));
            setDirty();
          },
        }), " " + lvl]));
      }
    }
    return U.el("div", { class: "lab-field" + (changed ? " changed" : "") }, [label, box]);
  }

  // Speeds: pick what sets each kind's speed; the chosen value is used, the other is kept but greyed out.
  const SPEED_ACTIVE = {
    road_posted_limit_kmh: (s) => s.road_speed_basis === "posted",
    road_achieved_cap_kmh: (s) => s.road_speed_basis === "achieved",
    bike_assisted_speed_kmh: (s) => s.bike_speed_basis === "assisted",
    bike_speed_limit_kmh: () => true,
  };
  function speedsEditor(f) {
    const prefix = f.key.split("_")[0];
    const s = S();
    const changed = !same(s[f.key], baseS()[f.key]);
    const seg = U.el("span", { class: "seg", role: "radiogroup", "aria-label": f.label }, Object.entries(f.choices).map(([k, text]) =>
      U.el("label", null, [U.el("input", { type: "radio", name: f.key, value: k, checked: s[f.key] === k, onchange: () => { S()[f.key] = k; setDirty(); } }), text])));
    const rows = state.schema.fields.filter((x) => x.sub && x.key.startsWith(prefix + "_")).map((x) => {
      const row = field(x);
      if (!SPEED_ACTIVE[x.key](s)) row.classList.add("inactive");
      return row;
    });
    let effective;
    if (prefix === "road") {
      const v = s.road_speed_basis === "posted" ? s.road_posted_limit_kmh : s.road_achieved_cap_kmh;
      effective = "Road vehicles run at the Appendix B formula speed, capped at " + (+v).toFixed(1) + " km/h (" + (v / 1.609344).toFixed(1) + " mph).";
    } else {
      const lim = s.bike_speed_limit_kmh;
      effective = (s.bike_speed_basis === "assisted" ? "E-bikes ride at " + s.bike_assisted_speed_kmh + " km/h" : "E-bikes ride at 700 × motor kW / total kg (about 1–8 km/h with a rider)") +
        (lim !== null && lim !== undefined ? ", capped at " + lim + " km/h." : ", no cap.");
    }
    return U.el("div", { class: "lab-speed" + (changed ? " changed" : "") }, [
      U.el("div", { class: "lab-label" }, [U.el("b", { text: prefix === "road" ? "Road vehicles" : "E-bikes" }), " ", U.el("a", { href: PLAN + f.q, target: "_blank", rel: "noopener", class: "small", text: "Q" + f.q })]),
      seg, ...rows, U.el("p", { class: "lab-effective", text: effective }),
    ]);
  }

  function demandEditor() {
    const rows = S().demand;
    const all = (state.schema.baseline.scenario.demand || []).map((r) => r[0]);
    const hours = Array.from(new Set([...all, ...rows.map((r) => r[0])])).sort((a, b) => a - b);
    const byHour = new Map(rows.map((r) => [r[0], r[1]]));
    const changed = !same(rows, baseS().demand);
    const grid = U.el("div", { class: "lab-demand" });
    for (const h of hours) {
      const on = byHour.has(h);
      const set = (include, val) => {
        const m = new Map(S().demand.map((r) => [r[0], r[1]]));
        if (include) m.set(h, val);
        else m.delete(h);
        if (m.size) S().demand = Array.from(m.entries()).sort((a, b) => a[0] - b[0]);
        setDirty();
      };
      grid.append(U.el("label", null, [
        U.el("input", { type: "checkbox", checked: on, title: "include this bin", onchange: (e) => set(e.target.checked, byHour.get(h) ?? 0) }),
        String(h).padStart(2, "0") + ":00",
        U.el("input", { type: "number", min: 0, step: 5, value: on ? byHour.get(h) : "", disabled: !on, "aria-label": "trips per hour from " + h + ":00",
          onchange: (e) => set(true, Math.max(0, Number(e.target.value) || 0)) }),
      ]));
    }
    const total = rows.reduce((s, r) => s + r[1], 0) * (rows.length > 1 ? rows[1][0] - rows[0][0] : 1);
    const scale = U.el("input", { type: "number", value: 1, step: 0.1, min: 0, "aria-label": "scale factor" });
    return U.el("div", { class: "lab-field" + (changed ? " changed" : ""), style: "display:block" }, [
      U.el("span", { class: "lab-label" }, ["Trips per hour, by 2-hour bin ", U.el("a", { href: PLAN + 5, target: "_blank", rel: "noopener", text: "Q5" })]),
      grid,
      U.el("div", { class: "lab-row small" }, [
        U.el("span", { class: "muted", text: total.toLocaleString() + " trips/day · scale all ×" }), scale,
        U.el("button", { type: "button", text: "Apply", onclick: () => { const k = Number(scale.value) || 1; S().demand = S().demand.map((r) => [r[0], Math.round(r[1] * k * 10) / 10]); setDirty(); } }),
      ]),
    ]);
  }

  function weightsEditor() {
    const w = state.config.weights;
    const sets = state.schema.weight_sets;
    const current = Object.keys(sets).find((k) => same(sets[k], w)) || "custom";
    const sum = state.schema.attributes.reduce((s, a) => s + (w[a] || 0), 0);
    const sel = U.el("select", { "aria-label": "weight set", onchange: (e) => { if (sets[e.target.value]) state.config.weights = clone(sets[e.target.value]); setDirty(); } },
      [...Object.keys(sets).map((k) => U.el("option", { value: k, text: k, selected: k === current })), U.el("option", { value: "custom", text: "custom", selected: current === "custom" })]);
    const fields = state.schema.attributes.map((a) => U.el("div", { class: "lab-field" }, [
      U.el("span", { class: "lab-label", text: U.label(a) }),
      U.el("span", { class: "lab-input" }, [U.el("input", { type: "number", min: 0, max: 1, step: 0.05, value: w[a] ?? 0, "aria-label": "weight " + a,
        onchange: (e) => { state.config.weights[a] = Math.max(0, Number(e.target.value) || 0); setDirty(); } })]),
    ]));
    return [
      U.el("div", { class: "lab-row" }, [sel, U.el("span", { class: "lab-sum small" + (Math.abs(sum - 1) > 1e-6 ? " bad" : ""), text: "sum " + sum.toFixed(3) }),
        U.el("button", { type: "button", text: "Normalize", onclick: () => { const t = state.schema.attributes.reduce((s, a) => s + (w[a] || 0), 0) || 1; for (const a of state.schema.attributes) w[a] = Math.round(((w[a] || 0) / t) * 1e4) / 1e4; const r = 1 - state.schema.attributes.reduce((s, a) => s + w[a], 0); w[state.schema.attributes[0]] += r; setDirty(); } })]),
      ...fields,
    ];
  }

  const segText = (segs) => segs.map((s) => s[0] + "-" + s[1] + ":" + s[2]).join(", ");
  function parseSegs(text) {
    const out = [];
    for (const part of text.split(",").map((p) => p.trim()).filter(Boolean)) {
      const m = part.match(/^(\d+)\s*-\s*(\d+)\s*:\s*(\d+)$/);
      if (!m) return null;
      out.push([+m[1], +m[2], +m[3]]);
    }
    return out.length ? out : null;
  }
  function gridEditor() {
    return ["road", "bike"].map((kind) => {
      const v = state.config.grid[kind];
      const changed = state.base && !same(v, state.base.grid[kind]);
      const count = v.reduce((n, s) => n + Math.floor((s[1] - s[0]) / s[2]) + 1, 0);
      return U.el("div", { class: "lab-field" + (changed ? " changed" : "") }, [
        U.el("span", { class: "lab-label" }, [kind === "road" ? "Road fleet sizes" : "Bike fleet sizes", U.el("a", { href: PLAN + 14, target: "_blank", rel: "noopener", text: "Q14" }),
          U.el("div", { class: "muted small", text: count + " sizes · start-stop:step" })]),
        U.el("span", { class: "lab-input" }, [U.el("input", { type: "text", value: segText(v), "aria-label": kind + " fleet sizes",
          onchange: (e) => { const p = parseSegs(e.target.value); if (p) { state.config.grid[kind] = p; setDirty(); } else e.target.setCustomValidity("use e.g. 5-50:5, 75-250:25"), e.target.reportValidity(); } })]),
      ]);
    });
  }

  function renderForm() {
    const form = $("form");
    const open = new Set([...form.querySelectorAll("details[open]")].map((d) => d.dataset.group));
    const firstRender = !form.childElementCount;
    form.textContent = "";
    const preset = state.presets.find((p) => p.id === state.presetId);
    const groups = {};
    for (const p of state.presets) (groups[p.group] = groups[p.group] || []).push(p);
    const sel = U.el("select", { id: "preset", "aria-label": "preset", onchange: (e) => applyPreset(e.target.value) },
      [U.el("option", { value: "", text: "— custom —", selected: !preset }), ...Object.entries(groups).map(([g, ps]) =>
        U.el("optgroup", { label: g }, ps.map((p) => U.el("option", { value: p.id, text: p.name, selected: p.id === state.presetId }))))]);
    form.append(U.el("div", { class: "lab-row" }, [U.el("b", { text: "Preset" }), sel]));
    if (preset) {
      form.append(U.el("p", { class: "small muted", style: "margin:4px 0", text: preset.description }),
        U.el("ul", { class: "lab-assume" }, preset.assumptions.map((a) => U.el("li", { text: a }))));
    }
    const nChanged = state.base ? countChanged(state.config, state.base) : 0;
    form.append(U.el("div", { class: "lab-row" }, [
      U.el("label", { class: "small" }, ["Name ", U.el("input", { type: "text", value: state.config.name, "aria-label": "config name", onchange: (e) => { state.config.name = e.target.value; setDirty(); } })]),
    ]), U.el("div", { class: "lab-row small" }, [
      U.el("span", { class: "muted", text: nChanged ? nChanged + " input" + (nChanged > 1 ? "s" : "") + " changed from " + (preset ? "the preset" : "the baseline") : "no changes from " + (preset ? "the preset" : "the baseline") }),
      nChanged ? U.el("button", { type: "button", text: "Reset", onclick: () => { state.config = clone(state.base); setDirty(); } }) : null,
      U.el("button", { type: "button", text: "Save config", onclick: saveConfig }),
      U.el("button", { type: "button", text: "Export", onclick: () => download(slug(state.config.name) + ".config.json", { kind: "os4-lab-config", config: state.config }) }),
    ]));
    const battery = U.el("span", { class: "seg", role: "radiogroup", "aria-label": "battery case" }, ["fixed", "removable"].map((k) =>
      U.el("label", null, [U.el("input", { type: "radio", name: "battery", value: k, checked: state.config.battery_case === k, onchange: () => { state.config.battery_case = k; setDirty(); } }), k === "fixed" ? "Fixed batteries" : "Removable"])));
    form.append(U.el("div", { class: "lab-row" }, [U.el("span", { class: "small", text: "E-bike batteries" }), battery, U.el("a", { href: PLAN + 15, target: "_blank", rel: "noopener", class: "small", text: "Q15" })]));

    const sections = {};
    const section = (name) => sections[name] || (sections[name] = []);
    for (const f of state.schema.fields) {
      if (f.sub) continue; // drawn inside its speed choice
      section(f.group).push(f.kind === "demand" ? demandEditor() : f.kind === "speeds" ? speedsEditor(f) : field(f));
    }
    section("Utility weights").push(...weightsEditor());
    section("Fleet grid").push(...gridEditor());
    for (const [name, nodes] of Object.entries(sections)) {
      const changed = nodes.filter((n) => n.classList && n.classList.contains("changed")).length;
      const d = U.el("details", { "data-group": name, open: firstRender ? (name === "Demand" || name === "Speeds") : open.has(name) },
        [U.el("summary", null, [name, changed ? U.el("span", { class: "badge", text: changed + " changed" }) : null]), ...nodes]);
      form.append(d);
    }
  }

  function countChanged(a, b) {
    let n = 0;
    for (const k of Object.keys(a.scenario)) if (!same(a.scenario[k], b.scenario[k])) n++;
    if (!same(a.weights, b.weights)) n++;
    if (!same(a.grid, b.grid)) n++;
    if (a.battery_case !== b.battery_case) n++;
    return n;
  }

  function applyPreset(id) {
    const p = state.presets.find((x) => x.id === id);
    state.presetId = p ? id : null;
    if (p) {
      state.base = clone(p.config);
      state.config = clone(p.config);
    } else state.base = clone(state.config);
    setDirty();
  }

  // ---------- calculate ----------
  let calcTimer = null;
  let running = null;
  function scheduleCalc() {
    clearTimeout(calcTimer);
    calcTimer = setTimeout(calculate, 800);
  }
  function showProgress(frac, text, indeterminate) {
    const box = $("progress");
    box.hidden = false;
    box.classList.toggle("indeterminate", !!indeterminate);
    $("progress-fill").style.width = indeterminate ? "" : Math.round(frac * 100) + "%";
    $("progress-text").textContent = text;
    box.setAttribute("role", "progressbar");
    box.setAttribute("aria-valuenow", Math.round(frac * 100));
  }
  async function calculate() {
    const token = {};
    running = token;
    $("error").hidden = true;
    $("calc").disabled = true;
    const t0 = performance.now();
    const secs = () => ((performance.now() - t0) / 1000).toFixed(1) + " s";
    showProgress(0, "Starting…", true);
    try {
      const { job_id } = await api("/api/jobs", state.config);
      for (;;) {
        await new Promise((r) => setTimeout(r, 200));
        if (running !== token) return; // a newer run replaced this one
        const job = await api("/api/jobs/" + job_id);
        if (job.status === "queued") showProgress(0, "Waiting for the worker… " + secs(), true);
        else if (job.status === "running") showProgress(job.progress, (job.progress < 1 ? "Scoring architectures " + Math.round(job.progress * 100) + "%" : "Summarizing front, anchors and architectures") + " · " + secs(), job.progress >= 1);
        else if (job.status === "error") throw new Error(job.error);
        else if (job.status === "done") {
          state.result = job.result;
          showProgress(1, (job.result.cached ? "Loaded from cache" : "Done") + " · " + secs(), false);
          setTimeout(() => running === token && ($("progress").hidden = true), 1500);
          renderResults();
          return;
        }
      }
    } catch (e) {
      $("progress").hidden = true;
      $("error").hidden = false;
      $("error").textContent = "Run failed: " + e.message;
    } finally {
      if (running === token) $("calc").disabled = false;
    }
  }

  // ---------- results ----------
  const card = (title, stat, sub) => U.el("div", { class: "card" }, [U.el("div", { class: "muted small", text: title }), U.el("div", { class: "stat", text: stat }), sub ? U.el("div", { class: "muted", text: sub }) : null]);

  function renderResults() {
    const r = state.result;
    const out = $("results");
    out.textContent = "";
    $("save-run").disabled = $("export-run").disabled = !r;
    if (!r) return;
    $("run-note").textContent = r.name + (r.cached ? " · cached" : "");
    const s = r.summary;
    if (!s.feasible) {
      out.append(U.el("div", { class: "banner", text: "No architecture meets the Table 1 thresholds and ceilings under these inputs (" + r.grid_size.toLocaleString() + " scored)." }),
        failures(r));
      return;
    }
    const fc = s.front_counts;
    out.append(U.el("div", { class: "cards" }, [
      card("Feasible architectures", s.feasible.toLocaleString(), r.screened_out.toLocaleString() + " screened out of " + r.grid_size.toLocaleString()),
      card("Cheapest feasible", U.money(s.cheapest.cost), s.cheapest.fleet + " · MAU " + s.cheapest.mau.toFixed(3)),
      card("First front point with MAU ≥ " + KNEE, s.knee ? U.money(s.knee.cost) : "none", s.knee ? s.knee.fleet + " · MAU " + s.knee.mau.toFixed(3) : "the MAU never reaches " + KNEE),
      card("Best MAU", s.max_mau.toFixed(3), "ceiling with these weights " + s.mau_ceiling.toFixed(3)),
      card("Pareto front", (fc["road-only"] + fc["bike-only"] + fc.mixed).toLocaleString() + " points", fc["road-only"] + " road / " + fc["bike-only"] + " bike / " + fc.mixed + " mixed"),
      card("Front meeting goals", Math.round(s.front_travel_ok * 100) + "% travel", Math.round(s.front_wait_ok * 100) + "% wait goal"),
    ]));
    if (r.notes.length) out.append(U.el("ul", { class: "lab-notes" }, r.notes.map((n) => U.el("li", { text: n }))));
    out.append(chartBlock([{ label: r.name, front: r.front, color: U.css("--accent") }], r.scatter, r.markers));
    out.append(U.el("h2", { text: "Cheapest fleet of each type" }));
    tableOf(out, Object.entries(s.cheapest_by_type).map(([t, p]) => ({ fleet_type: t, ...p })),
      [["fleet_type", "type"], ["fleet", "fleet"], ["cost", "cost", U.money], ["mau", "MAU"], ["wait_time", "wait (min)"], ["travel_time", "travel (min)"], ["availability", "availability"]]);
    if (r.markers.length) {
      out.append(U.el("h2", { text: "Reference architecture and anchors" }));
      tableOf(out, r.markers, [["architecture", "architecture"], ["fleet", "fleet"], ["fleet_cost_usd", "cost"], ["mau", "MAU"], ["wait_time", "wait (min)"], ["availability", "availability"], ["meets_thresholds", "meets thresholds"], ["dominated", "dominated"], ["cheaper_same_mau", "same MAU, cheapest on front"]]);
    }
    if (r.architectures.length) {
      out.append(U.el("h2", { text: "The five Task 2 architectures under these inputs" }));
      tableOf(out, r.architectures, [["architecture", "architecture"], ["fleet_cost_usd", "cost"], ["mau", "MAU"], ["peak_throughput", "throughput"], ["wait_time", "wait (min)"], ["availability", "availability"], ["travel_time", "travel (min)"], ["meets_thresholds", "meets thresholds"]]);
    }
    out.append(U.el("h2", { text: "Pareto front" }));
    tableOf(out, r.front, [["fleet_type", "type"], ["road_variant", "road vehicle"], ["n_road", "road N"], ["bike_variant", "bike"], ["n_bike", "bike N"], ["fleet_cost_usd", "cost"], ["mau", "MAU"], ["wait_time", "wait (min)"], ["availability", "availability"], ["travel_time", "travel (min)"], ["trips_per_vehicle_day", "riders/vehicle/day"], ["meets_travel_goal", "travel goal"]], 25);
    out.append(failures(r));
  }

  function failures(r) {
    const f = r.threshold_failures || {};
    const names = { daily_volume: "daily volume", peak_throughput: "peak throughput", offpeak_throughput: "off-peak throughput", bike_ceiling: "bike riders/day ceiling", car_ceiling: "car rides/day ceiling" };
    return U.el("p", { class: "muted small", text: "Screened out (an architecture can fail several): " + Object.entries(f).map(([k, v]) => (names[k] || k) + " " + v.toLocaleString()).join(" · ") });
  }

  function tableOf(container, rows, cols, pageSize) {
    const box = U.el("div");
    container.append(box);
    U.Table(box, {
      rows: () => rows, pageSize: pageSize || 50,
      columns: cols.map(([key, label, fmt]) => ({ key, label, num: typeof rows.find((x) => x[key] !== null && x[key] !== undefined)?.[key] === "number", fmt: fmt ? (v) => fmt(v) : null })),
    });
  }

  // ---------- chart: sampled tradespace, fronts, markers ----------
  function col(scatter, name) {
    const c = scatter.columns.find((x) => x.name === name);
    if (!c) return null;
    const v = scatter.data[name];
    return c.kind === "cat" ? v.map((i) => (i < 0 ? null : scatter.dicts[name][i])) : v;
  }

  function chartBlock(series, scatter, markers) {
    const wrap = U.el("div", { class: "lab-chart" });
    const canvas = U.el("canvas", { role: "img", "aria-label": "Tradespace: MAU against fleet cost" });
    const zoom = U.el("label", { class: "small" }, [U.el("input", { type: "checkbox", checked: state.zoom, onchange: (e) => { state.zoom = e.target.checked; draw(); } }), " zoom to fleets under $1.5M"]);
    const legend = U.el("div", { class: "lab-legend" });
    wrap.append(U.el("div", { class: "lab-row" }, [zoom]), canvas, legend);
    const pts = scatter ? { x: col(scatter, "fleet_cost_usd"), y: col(scatter, "mau"), t: col(scatter, "fleet_type"), rv: col(scatter, "road_variant"), nr: col(scatter, "n_road"), bv: col(scatter, "bike_variant"), nb: col(scatter, "n_bike") } : null;
    let geom = null;
    function draw() {
      const dpr = window.devicePixelRatio || 1;
      const W = canvas.clientWidth || 800, H = canvas.clientHeight || 440;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const xs = [], ys = [];
      for (const s of series) for (const p of s.front) xs.push(p.fleet_cost_usd), ys.push(p.mau);
      if (pts) pts.x.forEach((v, i) => (xs.push(v), ys.push(pts.y[i])));
      for (const m of markers || []) xs.push(m.fleet_cost_usd), ys.push(m.mau);
      if (!xs.length) return;
      const x0 = Math.min(...xs) * 0.9, x1 = state.zoom ? Math.min(1.5e6, Math.max(...xs)) : Math.max(...xs) * 1.1;
      const visY = ys.filter((_, i) => xs[i] <= x1);
      const y0 = Math.max(0, Math.min(...visY) - 0.02), y1 = Math.min(1, Math.max(...visY) + 0.02);
      const L = 48, R = 14, T = 22, B = 40;
      const sx = (v) => L + ((Math.log(v) - Math.log(x0)) / (Math.log(x1) - Math.log(x0))) * (W - L - R);
      const sy = (v) => T + (1 - (v - y0) / (y1 - y0)) * (H - T - B);
      geom = { sx, sy, x1 };
      ctx.strokeStyle = U.css("--grid");
      ctx.fillStyle = U.css("--ink-2");
      ctx.font = "11px " + U.css("--font");
      ctx.lineWidth = 1;
      for (let e = Math.floor(Math.log10(x0)); e <= Math.ceil(Math.log10(x1)); e++) {
        for (const m of [1, 2, 5]) {
          const v = m * 10 ** e;
          if (v < x0 || v > x1) continue;
          const X = sx(v);
          ctx.beginPath(); ctx.moveTo(X, T); ctx.lineTo(X, H - B); ctx.stroke();
          ctx.fillText(U.moneyShort(v), X - 14, H - B + 14);
        }
      }
      for (let k = 0; k <= 5; k++) {
        const v = y0 + ((y1 - y0) * k) / 5, Y = sy(v);
        ctx.beginPath(); ctx.moveTo(L, Y); ctx.lineTo(W - R, Y); ctx.stroke();
        ctx.fillText(v.toFixed(2), 8, Y + 4);
      }
      ctx.fillText("fleet cost (log scale)", W / 2 - 40, H - 8);
      ctx.fillText("MAU", 8, 12);
      ctx.save();
      ctx.beginPath(); ctx.rect(L, T, W - L - R, H - T - B); ctx.clip();
      if (pts) {
        ctx.globalAlpha = 0.35;
        pts.x.forEach((v, i) => {
          if (v > x1) return;
          ctx.fillStyle = U.typeColor(pts.t[i]);
          ctx.fillRect(sx(v) - 1.5, sy(pts.y[i]) - 1.5, 3, 3);
        });
        ctx.globalAlpha = 1;
      }
      for (const s of series) {
        ctx.strokeStyle = s.color;
        ctx.lineWidth = 2;
        ctx.setLineDash(s.dash || []);
        ctx.beginPath();
        s.front.forEach((p, i) => {
          const X = sx(p.fleet_cost_usd), Y = sy(p.mau);
          if (i === 0) ctx.moveTo(X, Y);
          else { ctx.lineTo(X, sy(s.front[i - 1].mau)); ctx.lineTo(X, Y); }
        });
        ctx.stroke();
        ctx.setLineDash([]);
      }
      for (const m of markers || []) {
        const X = sx(m.fleet_cost_usd), Y = sy(m.mau);
        ctx.fillStyle = m.role === "reference" ? U.css("--bad") : U.css("--ink");
        ctx.beginPath(); ctx.moveTo(X, Y - 6); ctx.lineTo(X + 6, Y); ctx.lineTo(X, Y + 6); ctx.lineTo(X - 6, Y); ctx.closePath(); ctx.fill();
        ctx.fillStyle = U.css("--ink-2");
        ctx.fillText(m.role === "reference" ? "reference" : m.architecture.split(" (")[0], X + 8, Y - 6);
      }
      ctx.restore();
    }
    legend.append(...series.map((s) => U.el("span", null, [U.el("span", { class: "sw", style: "background:" + s.color }), s.label + " front (" + s.front.length + ")"])));
    if (pts) legend.append(...U.TYPES.map((t) => U.el("span", null, [U.el("span", { class: "sw", style: "opacity:.5;background:" + U.typeColor(t) }), t + " (sample)"])));
    if (markers && markers.length) legend.append(U.el("span", { text: "◆ reference (red) and anchors" }));
    canvas.addEventListener("pointermove", (e) => {
      if (!geom || !pts) return;
      const rect = canvas.getBoundingClientRect();
      const mx = e.clientX - rect.left, my = e.clientY - rect.top;
      let best = -1, bd = 64;
      pts.x.forEach((v, i) => {
        if (v > geom.x1) return;
        const d = (geom.sx(v) - mx) ** 2 + (geom.sy(pts.y[i]) - my) ** 2;
        if (d < bd) (bd = d), (best = i);
      });
      const tip = $("tip");
      if (best < 0) return (tip.hidden = true);
      tip.hidden = false;
      tip.textContent = U.archId({ n_road: pts.nr[best], road_variant: pts.rv[best], n_bike: pts.nb[best], bike_variant: pts.bv[best] }) + " · " + U.money(pts.x[best]) + " · MAU " + pts.y[best].toFixed(3);
      tip.style.left = e.pageX + 12 + "px";
      tip.style.top = e.pageY + 12 + "px";
    });
    canvas.addEventListener("pointerleave", () => ($("tip").hidden = true));
    requestAnimationFrame(draw);
    new ResizeObserver(() => draw()).observe(canvas);
    return wrap;
  }

  // ---------- saving ----------
  function saveConfig() {
    const name = prompt("Save config as:", state.config.name);
    if (!name) return;
    const list = load(STORE.configs, []).filter((c) => c.name !== name);
    list.unshift({ name, savedAt: new Date().toISOString(), config: { ...clone(state.config), name } });
    store(STORE.configs, list) ? renderSaved() : alert("Could not save: browser storage is unavailable or full. Export to a file instead.");
  }
  function runRecord(r) {
    return { id: r.key + "-" + Date.now().toString(36), name: r.name, savedAt: new Date().toISOString(), config: r.config, summary: r.summary, front: r.front, notes: r.notes };
  }
  function saveRun() {
    if (!state.result) return;
    let runs = [runRecord(state.result), ...load(STORE.runs, [])].slice(0, MAX_RUNS);
    while (runs.length && !store(STORE.runs, runs)) runs = runs.slice(0, -1); // evict oldest on quota
    $("run-note").textContent = runs.length ? "Saved “" + state.result.name + "” · " + runs.length + " saved runs" : "Could not save (storage unavailable)";
    renderSaved();
    renderComparePick();
  }

  function renderSaved() {
    const configs = load(STORE.configs, []);
    const runs = load(STORE.runs, []);
    const cbox = $("saved-configs"), rbox = $("saved-runs");
    cbox.textContent = rbox.textContent = "";
    const when = (s) => new Date(s).toLocaleString();
    cbox.append(configs.length ? U.el("div", { class: "lab-list" }, configs.map((c, i) => U.el("div", { class: "item" }, [
      U.el("span", { class: "grow" }, [U.el("b", { text: c.name }), U.el("span", { class: "muted small", text: " · " + when(c.savedAt) })]),
      U.el("button", { type: "button", text: "Load", onclick: () => { state.config = clone(c.config); state.base = clone(c.config); state.presetId = null; setDirty(); showTab("run"); } }),
      U.el("button", { type: "button", text: "Export", onclick: () => download(slug(c.name) + ".config.json", { kind: "os4-lab-config", config: c.config }) }),
      U.el("button", { type: "button", text: "Delete", onclick: () => { configs.splice(i, 1); store(STORE.configs, configs); renderSaved(); } }),
    ]))) : U.el("p", { class: "muted", text: "No saved configs yet." }));
    rbox.append(runs.length ? U.el("div", { class: "lab-list" }, runs.map((r, i) => U.el("div", { class: "item" }, [
      U.el("span", { class: "grow" }, [U.el("b", { text: r.name }), U.el("span", { class: "muted small", text: " · " + when(r.savedAt) + " · knee " + (r.summary.knee ? U.money(r.summary.knee.cost) : "none") + " · cheapest " + (r.summary.cheapest ? U.money(r.summary.cheapest.cost) : "–") })]),
      U.el("button", { type: "button", text: "Open", onclick: () => { state.config = clone(r.config); state.base = clone(r.config); state.presetId = null; setDirty(); showTab("run"); calculate(); } }),
      U.el("button", { type: "button", text: "Export", onclick: () => download(slug(r.name) + ".run.json", { kind: "os4-lab-run", run: r }) }),
      U.el("button", { type: "button", text: "Delete", onclick: () => { runs.splice(i, 1); store(STORE.runs, runs); renderSaved(); renderComparePick(); } }),
    ]))) : U.el("p", { class: "muted", text: "No saved runs yet: press Calculate, then Save run." }));
    let bytes = 0;
    try { for (const k of Object.values(STORE)) bytes += (localStorage.getItem(k) || "").length; } catch (e) { /* storage blocked */ }
    $("storage-note").textContent = "Using about " + Math.round(bytes / 1024) + " KB of browser storage";
  }

  function importFile(file) {
    const reader = new FileReader();
    reader.onload = () => {
      try {
        const d = JSON.parse(reader.result);
        const configs = load(STORE.configs, []), runs = load(STORE.runs, []);
        let n = 0;
        const addConfig = (c) => { configs.unshift({ name: c.name || "imported", savedAt: new Date().toISOString(), config: c }); n++; };
        const addRun = (r) => { runs.unshift(r); n++; };
        if (d.kind === "os4-lab-config") addConfig(d.config);
        else if (d.kind === "os4-lab-run") addRun(d.run);
        else if (d.kind === "os4-lab-bundle") { (d.configs || []).forEach((c) => (configs.unshift(c), n++)); (d.runs || []).forEach(addRun); }
        else if (d.scenario && d.grid) addConfig(d);
        else throw new Error("not an OS4 Lab file");
        store(STORE.configs, configs);
        store(STORE.runs, runs.slice(0, MAX_RUNS));
        $("storage-note").textContent = "Imported " + n + " item" + (n === 1 ? "" : "s");
        renderSaved();
        renderComparePick();
      } catch (e) {
        alert("Import failed: " + e.message);
      }
    };
    reader.readAsText(file);
  }

  // ---------- compare ----------
  const COMPARE_COLORS = ["--road", "--bike", "--mixed", "--star"];
  function renderComparePick() {
    const runs = load(STORE.runs, []);
    const box = $("compare-pick");
    box.textContent = "";
    state.compare = state.compare.filter((id) => runs.some((r) => r.id === id));
    if (!runs.length) return box.append(U.el("span", { class: "muted", text: "Save some runs first (Run tab → Calculate → Save run)." }));
    for (const r of runs) {
      box.append(U.el("label", { class: "small" }, [U.el("input", {
        type: "checkbox", checked: state.compare.includes(r.id), disabled: !state.compare.includes(r.id) && state.compare.length >= 4,
        onchange: (e) => { state.compare = e.target.checked ? [...state.compare, r.id] : state.compare.filter((x) => x !== r.id); renderComparePick(); },
      }), " " + r.name + " (" + new Date(r.savedAt).toLocaleDateString() + ")"]));
    }
    renderCompare(runs.filter((r) => state.compare.includes(r.id)));
  }

  function renderCompare(runs) {
    const out = $("compare-out");
    out.textContent = "";
    if (runs.length < 1) return;
    out.append(chartBlock(runs.map((r, i) => ({ label: r.name, front: r.front, color: U.css(COMPARE_COLORS[i]), dash: i % 2 ? [6, 3] : [] })), null, null));
    const rows = [
      ["Feasible architectures", (s) => (s.feasible || 0).toLocaleString()],
      ["Cheapest feasible", (s) => (s.cheapest ? U.money(s.cheapest.cost) + " · " + s.cheapest.fleet : "–")],
      ["First front point with MAU ≥ " + KNEE, (s) => (s.knee ? U.money(s.knee.cost) + " · " + s.knee.fleet : "none")],
      ["Best MAU", (s) => (s.max_mau ?? 0).toFixed(3)],
      ["Front (road / bike / mixed)", (s) => (s.front_counts ? [s.front_counts["road-only"], s.front_counts["bike-only"], s.front_counts.mixed].join(" / ") : "–")],
      ["Front meeting travel goal", (s) => (s.front_travel_ok !== undefined ? Math.round(s.front_travel_ok * 100) + "%" : "–")],
    ];
    out.append(U.el("h2", { text: "Summary" }), simpleTable(["", ...runs.map((r) => r.name)], rows.map(([label, f]) => [label, ...runs.map((r) => f(r.summary))])));
    // Inputs that differ between the selected runs.
    const keys = new Set();
    const flat = runs.map((r) => {
      const o = { battery_case: r.config.battery_case, weights: r.config.weights, "grid.road": r.config.grid.road, "grid.bike": r.config.grid.bike };
      for (const [k, v] of Object.entries(r.config.scenario)) o[k] = v;
      Object.keys(o).forEach((k) => keys.add(k));
      return o;
    });
    const num = (x) => (typeof x === "number" ? String(+x.toFixed(3)) : x);
    const fmt = (v) => (v === null ? "off" : typeof v === "number" ? num(v) : Array.isArray(v) ? (Array.isArray(v[0]) ? v.map((x) => x.join(v[0].length === 3 ? "/" : ":")).join(", ") : v.join(", ")) : typeof v === "object" ? Object.entries(v).map(([a, w]) => a.split("_")[0] + " " + w).join(", ") : String(v));
    const label = (k) => (state.schema.fields.find((f) => f.key === k) || {}).label || k;
    const diff = [...keys].filter((k) => flat.some((o) => !same(o[k], flat[0][k])));
    out.append(U.el("h2", { text: "Inputs that differ" }), diff.length ? simpleTable(["input", ...runs.map((r) => r.name)], diff.map((k) => [label(k), ...flat.map((o) => fmt(o[k]))])) : U.el("p", { class: "muted", text: "The selected runs have identical inputs." }));
  }

  function simpleTable(head, rows) {
    return U.el("div", { class: "table-wrap" }, [U.el("table", { class: "lab-diff" }, [
      U.el("thead", null, [U.el("tr", null, head.map((h) => U.el("th", { text: h })))]),
      U.el("tbody", null, rows.map((r) => U.el("tr", null, r.map((c, i) => U.el(i ? "td" : "th", { text: c, scope: i ? null : "row" }))))),
    ])]);
  }

  // ---------- tabs & init ----------
  function showTab(name) {
    for (const t of ["run", "compare", "saved"]) $("tab-" + t).hidden = t !== name;
    document.querySelectorAll("[data-tab]").forEach((a) => (a.getAttribute("data-tab") === name ? a.setAttribute("aria-current", "page") : a.removeAttribute("aria-current")));
    if (name === "compare") renderComparePick();
    if (name === "saved") renderSaved();
  }

  async function init() {
    try {
      const [meta, schema, presets] = await Promise.all([api("/api/meta"), api("/api/schema"), api("/api/presets")]);
      OS4.meta = meta;
      state.schema = schema;
      state.presets = presets;
    } catch (e) {
      $("error").hidden = false;
      $("error").textContent = "Cannot reach the lab server (" + e.message + "). Start it with: uv run python -m os4.lab";
      return;
    }
    const saved = load(STORE.current, null);
    if (saved && saved.config) {
      state.config = saved.config;
      state.presetId = saved.presetId;
      const p = state.presets.find((x) => x.id === saved.presetId);
      state.base = clone(p ? p.config : state.schema.baseline);
    } else {
      state.presetId = "standard";
      state.base = clone(state.presets[0].config);
      state.config = clone(state.presets[0].config);
    }
    renderForm();
    $("calc").addEventListener("click", calculate);
    $("save-run").addEventListener("click", saveRun);
    $("export-run").addEventListener("click", () => state.result && download(slug(state.result.name) + ".run.json", { kind: "os4-lab-run", run: runRecord(state.result) }));
    $("export-all").addEventListener("click", () => download("os4-lab-saved.json", { kind: "os4-lab-bundle", configs: load(STORE.configs, []), runs: load(STORE.runs, []) }));
    $("import").addEventListener("change", (e) => e.target.files[0] && importFile(e.target.files[0]));
    document.querySelectorAll("[data-tab]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); showTab(a.getAttribute("data-tab")); history.replaceState(null, "", "#" + a.getAttribute("data-tab")); }));
    showTab((location.hash || "#run").slice(1) in { run: 1, compare: 1, saved: 1 } ? location.hash.slice(1) || "run" : "run");
  }
  init();
})();
