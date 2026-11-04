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
    if (res.status === 401 && data.auth) showLogin();
    if (!res.ok) throw new Error(data.error || res.statusText);
    return data;
  }

  // ---------- password ----------
  function showLogin() {
    $("login").hidden = false;
    for (const t of ["run", "compare", "saved"]) $("tab-" + t).hidden = true;
    document.querySelector(".topbar nav").style.visibility = "hidden";
    $("login-password").focus();
  }
  $("login-form").addEventListener("submit", async (e) => {
    e.preventDefault();
    $("login-error").textContent = "";
    try {
      await api("/api/login", { password: $("login-password").value });
      $("login").hidden = true;
      document.querySelector(".topbar nav").style.visibility = "";
      init();
    } catch (err) {
      $("login-error").textContent = err.message === "wrong password" ? "Wrong password." : err.message;
    }
  });

  // ---------- run-size limit (kept across presets and scenarios) ----------
  state.limit = load("os4lab.limit", true);
  let estimateTimer = null;
  function scheduleEstimate() {
    clearTimeout(estimateTimer);
    estimateTimer = setTimeout(updateEstimate, 300);
  }
  const millions = (n) => (n >= 1e6 ? (n / 1e6).toFixed(2) + " M" : n.toLocaleString());
  async function updateEstimate() {
    const box = $("estimate");
    try {
      const e = await api("/api/estimate", { config: state.config, limit: state.limit });
      box.classList.remove("over");
      box.textContent = e.limited
        ? "Full grid: " + millions(e.limited.from) + " architectures. With the limit this run scores " + millions(e.limited.to) +
          " (road fleets up to " + e.limited.road_max + ", bikes up to " + e.limited.bike_max + ")."
        : "This run scores " + millions(e.architectures) + " architectures.";
    } catch (err) {
      box.classList.add("over");
      box.textContent = err.message;
    }
  }

  // ---------- form ----------
  const S = () => state.config.scenario;
  const baseS = () => (state.base ? state.base.scenario : {});

  function setDirty() {
    store(STORE.current, { config: state.config, presetId: state.presetId });
    scheduleEstimate();
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
      const { job_id } = await api("/api/jobs", { config: state.config, tags: state.tags, limit: state.limit });
      for (;;) {
        await new Promise((r) => setTimeout(r, 200));
        if (running !== token) return; // a newer run replaced this one
        const job = await api("/api/jobs/" + job_id);
        if (job.status === "queued") showProgress(0, (job.position > 1 ? "Queued: " + (job.position - 1) + " run" + (job.position > 2 ? "s" : "") + " ahead of yours" : "Next in line") + " · " + secs(), true);
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
    if (r.limited) out.append(U.el("div", { class: "banner lab-limited", text: "Limited to " + millions(r.limited.limit) + " architectures: the full grid was " + millions(r.limited.from) +
      ", so this run kept road fleets up to " + r.limited.road_max + " and bike fleets up to " + r.limited.bike_max + " (" + millions(r.limited.to) + " scored). Untick the limit next to Calculate to run the full grid." }));
    if (r.notes.length) out.append(U.el("ul", { class: "lab-notes" }, r.notes.map((n) => U.el("li", { text: n }))));
    const chart = chartBlock([{ label: r.name, front: r.front, color: U.css("--accent") }], r.scatter, r.markers, { filters: true, tags: r.tags || [] });
    out.append(chart);
    out.append(U.el("h2", { text: "Tagged architectures" }), tagsSection(r.tags || []));
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
    tableOf(out, r.front, [["fleet_type", "type"], ["road_variant", "road vehicle"], ["n_road", "road N"], ["bike_variant", "bike"], ["n_bike", "bike N"], ["fleet_cost_usd", "cost"], ["mau", "MAU"], ["wait_time", "wait (min)"], ["availability", "availability"], ["travel_time", "travel (min)"], ["trips_per_vehicle_day", "riders/vehicle/day"], ["meets_travel_goal", "travel goal"]], 25,
      (row) => { chart.select(archOf(row)); chart.scrollIntoView({ behavior: "smooth", block: "center" }); });
    out.append(failures(r));
  }

  function failures(r) {
    const f = r.threshold_failures || {};
    const names = { daily_volume: "daily volume", peak_throughput: "peak throughput", offpeak_throughput: "off-peak throughput", bike_ceiling: "bike riders/day ceiling", car_ceiling: "car rides/day ceiling" };
    return U.el("p", { class: "muted small", text: "Screened out (an architecture can fail several): " + Object.entries(f).map(([k, v]) => (names[k] || k) + " " + v.toLocaleString()).join(" · ") });
  }

  function tableOf(container, rows, cols, pageSize, onRowClick) {
    const box = U.el("div");
    container.append(box);
    U.Table(box, {
      rows: () => rows, pageSize: pageSize || 50, onRowClick,
      columns: cols.map(([key, label, fmt]) => ({ key, label, num: typeof rows.find((x) => x[key] !== null && x[key] !== undefined)?.[key] === "number", fmt: fmt ? (v) => fmt(v) : null })),
    });
  }

  function col(scatter, name) {
    const c = scatter.columns.find((x) => x.name === name);
    if (!c) return null;
    const v = scatter.data[name];
    return c.kind === "cat" ? v.map((i) => (i < 0 ? null : scatter.dicts[name][i])) : v;
  }

  // ---------- chart: sampled tradespace, fronts, markers, tags; filters; drag to pan, scroll to zoom ----------
  const emptyFilters = () => ({ types: new Set(U.TYPES), road_chassis: new Set(), autonomy: new Set(), bike_frame: new Set(), battery: new Set(), spares: new Set(), n_road: [null, null], n_bike: [null, null], cost: [null, null], minU: null, flags: new Set() });
  state.filters = emptyFilters();
  const FLAG_LABELS = { meets_wait_goal: "wait goal", meets_travel_goal: "travel-time goal", meets_availability_benchmark: "0.75 availability" };
  const archOf = (r) => ({ n_road: r.n_road || 0, road_variant: r.road_variant, n_bike: r.n_bike || 0, bike_variant: r.bike_variant });
  const sameArch = (a, b) => U.archId(a) === U.archId(b);

  function chartBlock(series, scatter, markers, opts) {
    opts = opts || {};
    const wrap = U.el("div", { class: "lab-chart" });
    const canvas = U.el("canvas", { role: "img", "aria-label": "Tradespace: MAU against fleet cost. Drag to pan, scroll to zoom, double-click to reset, click a point to select it." });
    const zoom = U.el("label", { class: "small" }, [U.el("input", { type: "checkbox", checked: state.zoom, onchange: (e) => { state.zoom = e.target.checked; view = null; draw(); } }), " start zoomed to fleets under $1.5M"]);
    const reset = U.el("button", { type: "button", text: "Reset view", onclick: () => { view = null; draw(); } });
    const legend = U.el("div", { class: "lab-legend" });
    const countLine = U.el("p", { class: "muted small", style: "margin:4px 2px" });
    const details = U.el("div", { class: "lab-details", hidden: true });
    const pts = scatter ? { x: col(scatter, "fleet_cost_usd"), y: col(scatter, "mau"), t: col(scatter, "fleet_type"), rv: col(scatter, "road_variant"), nr: col(scatter, "n_road"), bv: col(scatter, "bike_variant"), nb: col(scatter, "n_bike"),
      wait: col(scatter, "wait_time"), avail: col(scatter, "availability"), travel: col(scatter, "travel_time") } : null;
    // Per-point categories for the filters, decoded from the variant ids (C6-P1-G3-M3-A3, B1-E1-G2-K1-S1.5).
    if (pts) {
      pts.chassis = pts.rv.map((v) => (v ? v.split("-")[0] : null));
      pts.autonomy = pts.rv.map((v) => (v ? v.split("-")[4] : null));
      pts.frame = pts.bv.map((v) => (v ? v.split("-")[0] : null));
      pts.battery = pts.bv.map((v) => (v ? v.split("-")[1] : null));
      pts.spares = pts.bv.map((v) => (v ? (v.split("-")[4] || "fixed") : null));
      for (const k of Object.keys(FLAG_LABELS)) pts[k] = col(scatter, k);
    }
    const tags = opts.tags || [];
    let visible = pts ? pts.x.map(() => true) : null;
    let filteredFront = null;
    const f = state.filters;

    function filtersActive() {
      return f.types.size < 3 || [f.road_chassis, f.autonomy, f.bike_frame, f.battery, f.spares, f.flags].some((s) => s.size) || f.minU !== null || [f.n_road, f.n_bike, f.cost].some((r) => r[0] !== null || r[1] !== null);
    }
    function applyFilters() {
      if (!pts) return;
      const inR = (v, r) => (r[0] === null || v >= r[0]) && (r[1] === null || v <= r[1]);
      const inS = (v, s) => !s.size || (v !== null && s.has(v));
      visible = pts.x.map((c, i) =>
        f.types.has(pts.t[i]) && inS(pts.chassis[i], f.road_chassis) && inS(pts.autonomy[i], f.autonomy) && inS(pts.frame[i], f.bike_frame) &&
        inS(pts.battery[i], f.battery) && inS(pts.spares[i], f.spares) && inR(pts.nr[i] || 0, f.n_road) && inR(pts.nb[i] || 0, f.n_bike) &&
        inR(c, [f.cost[0] === null ? null : f.cost[0] * 1e6, f.cost[1] === null ? null : f.cost[1] * 1e6]) && (f.minU === null || pts.y[i] >= f.minU) &&
        [...f.flags].every((k) => !pts[k] || pts[k][i] === 1));
      filteredFront = null;
      if (filtersActive()) {
        const idx = pts.x.map((_, i) => i).filter((i) => visible[i]).sort((a, b) => pts.x[a] - pts.x[b] || pts.y[b] - pts.y[a]);
        let best = -Infinity;
        filteredFront = [];
        for (const i of idx) if (pts.y[i] > best) (best = pts.y[i]), filteredFront.push(i);
      }
      const n = visible.filter(Boolean).length;
      countLine.textContent = "Showing " + n.toLocaleString() + " of " + pts.x.length.toLocaleString() + " plotted architectures (every road-only, bike-only and front point, plus a sample of mixed fleets)" +
        (filteredFront ? "; the dashed line is the front of the filtered points." : ".");
      draw();
    }

    // Big toggle buttons: empty selection = all.
    function chips(title, values, set, labelFor) {
      const row = U.el("div", { class: "chips", role: "group", "aria-label": title });
      for (const v of values) {
        const b = U.el("button", { type: "button", class: "chip", "aria-pressed": set.has(v) ? "true" : "false" }, labelFor ? labelFor(v) : v);
        b.addEventListener("click", () => { set.has(v) ? set.delete(v) : set.add(v); b.setAttribute("aria-pressed", set.has(v) ? "true" : "false"); applyFilters(); });
        row.append(b);
      }
      return U.el("div", { class: "f" }, [U.el("span", { text: title }), row]);
    }
    function rangeInputs(title, key, step) {
      const mk = (j, ph) => {
        const i = U.el("input", { type: "number", placeholder: ph, step, min: 0, value: f[key][j] ?? "", "aria-label": title + " " + ph });
        i.addEventListener("input", () => { f[key][j] = i.value === "" ? null : +i.value; applyFilters(); });
        return i;
      };
      return U.el("div", { class: "f" }, [U.el("span", { text: title }), U.el("div", { class: "range" }, [mk(0, "min"), "–", mk(1, "max")])]);
    }
    function filterPanel() {
      const uniq = (a) => Array.from(new Set(a.filter((v) => v !== null))).sort((x, y) => x.localeCompare(y, undefined, { numeric: true }));
      const box = U.el("div", { class: "filters lab-filters", "aria-label": "Filters" });
      const types = U.el("div", { class: "chips", role: "group", "aria-label": "fleet type" }, U.TYPES.map((t) => {
        const b = U.el("button", { type: "button", class: "chip", "aria-pressed": f.types.has(t) ? "true" : "false" }, [U.shapeSvg(U.typeShape(t), U.typeColor(t), 12), " " + t]);
        b.addEventListener("click", () => { f.types.has(t) ? f.types.delete(t) : f.types.add(t); b.setAttribute("aria-pressed", f.types.has(t) ? "true" : "false"); applyFilters(); });
        return b;
      }));
      box.append(U.el("div", { class: "f" }, [U.el("span", { text: "fleet type" }), types]));
      box.append(chips("road chassis", uniq(pts.chassis), f.road_chassis));
      box.append(chips("autonomy", uniq(pts.autonomy), f.autonomy));
      box.append(chips("bike frame", uniq(pts.frame), f.bike_frame));
      box.append(chips("bike battery", uniq(pts.battery), f.battery));
      if (uniq(pts.spares).length > 1) box.append(chips("spare packs", uniq(pts.spares), f.spares, (v) => (v === "fixed" ? "fixed" : v.slice(1) + " spare")));
      box.append(rangeInputs("N road", "n_road", 1), rangeInputs("N bike", "n_bike", 5), rangeInputs("cost ($M)", "cost", 0.1));
      const minU = U.el("input", { type: "number", placeholder: "e.g. 0.9", step: 0.01, min: 0, max: 1, value: f.minU ?? "", "aria-label": "minimum MAU" });
      minU.addEventListener("input", () => { f.minU = minU.value === "" ? null : +minU.value; applyFilters(); });
      box.append(U.el("div", { class: "f" }, [U.el("span", { text: "min MAU" }), minU]));
      box.append(chips("only architectures meeting", Object.keys(FLAG_LABELS).filter((k) => pts[k]), f.flags, (k) => FLAG_LABELS[k]));
      box.append(U.el("div", { class: "f" }, [U.el("span", { text: " " }), U.el("button", { type: "button", class: "chip", text: "Reset filters", onclick: () => { state.filters = emptyFilters(); renderResults(); } })]));
      return box;
    }

    // Everything hoverable/selectable: sampled points (visible only), front points, reference and anchors, tags.
    function hoverItems() {
      const items = [];
      if (pts) pts.x.forEach((x, i) => visible[i] && items.push({ x, y: pts.y[i], arch: { n_road: pts.nr[i], road_variant: pts.rv[i], n_bike: pts.nb[i], bike_variant: pts.bv[i] }, wait: pts.wait[i], avail: pts.avail[i], travel: pts.travel[i] }));
      for (const s of series) for (const p of s.front) items.push({ x: p.fleet_cost_usd, y: p.mau, arch: archOf(p), where: series.length > 1 ? s.label : "front", wait: p.wait_time, avail: p.availability, travel: p.travel_time });
      for (const m of markers || []) items.push({ x: m.fleet_cost_usd, y: m.mau, arch: archOf(m), where: m.architecture, wait: m.wait_time, avail: m.availability, travel: m.travel_time });
      for (const t of tags) if (t.mau !== undefined) items.push({ x: t.fleet_cost_usd, y: t.mau, arch: archOf(t), where: "★ " + t.label, wait: t.wait_time, avail: t.availability, travel: t.travel_time });
      return items;
    }

    const M = { l: 48, r: 14, t: 22, b: 40 };
    let W = 800, H = 440, view = null;
    function defaultView() {
      const items = hoverItems();
      if (!items.length) return { x0: Math.log(1e5), x1: Math.log(1e7), y0: 0, y1: 1 };
      let x0 = Infinity, x1 = -Infinity;
      for (const h of items) (x0 = Math.min(x0, h.x)), (x1 = Math.max(x1, h.x));
      x0 *= 0.9;
      x1 = state.zoom ? Math.min(1.5e6, x1 * 1.05) : x1 * 1.1;
      let y0 = Infinity, y1 = -Infinity;
      for (const h of items) if (h.x <= x1) (y0 = Math.min(y0, h.y)), (y1 = Math.max(y1, h.y));
      const py = (y1 - y0) * 0.05 || 0.02;
      return { x0: Math.log(x0), x1: Math.log(Math.max(x1, x0 * 1.5)), y0: Math.max(0, y0 - py), y1: Math.min(1.02, y1 + py) };
    }
    const V = () => view || (view = defaultView());
    const sx = (cost) => M.l + ((Math.log(cost) - V().x0) / (V().x1 - V().x0)) * (W - M.l - M.r);
    const sy = (u) => M.t + ((V().y1 - u) / (V().y1 - V().y0)) * (H - M.t - M.b);
    const invX = (px) => V().x0 + ((px - M.l) / (W - M.l - M.r)) * (V().x1 - V().x0);
    const invY = (py) => V().y1 - ((py - M.t) / (H - M.t - M.b)) * (V().y1 - V().y0);
    let picked = null;

    function stepLine(ctx, xs, ys) {
      ctx.beginPath();
      xs.forEach((c, i) => { const X = sx(c), Y = sy(ys[i]); if (i === 0) ctx.moveTo(X, Y); else { ctx.lineTo(X, sy(ys[i - 1])); ctx.lineTo(X, Y); } });
      ctx.stroke();
    }
    // Same shapes as the explorer: circle = road-only, triangle = bike-only, square = mixed.
    function shape(ctx, type, x, y, r) {
      if (type === "road-only") { ctx.moveTo(x + r, y); ctx.arc(x, y, r, 0, Math.PI * 2); }
      else if (type === "bike-only") { const h = r * 1.25; ctx.moveTo(x, y - h); ctx.lineTo(x + h, y + h * 0.8); ctx.lineTo(x - h, y + h * 0.8); ctx.closePath(); }
      else { const h = r * 0.9; ctx.rect(x - h, y - h, 2 * h, 2 * h); }
    }
    function star(ctx, X, Y, r) {
      ctx.beginPath();
      for (let k = 0; k < 10; k++) { const a = -Math.PI / 2 + (k * Math.PI) / 5, rr = k % 2 ? r * 0.45 : r; ctx.lineTo(X + rr * Math.cos(a), Y + rr * Math.sin(a)); }
      ctx.closePath();
    }
    function draw() {
      const dpr = window.devicePixelRatio || 1;
      W = canvas.clientWidth || 800;
      H = canvas.clientHeight || 440;
      canvas.width = W * dpr;
      canvas.height = H * dpr;
      const ctx = canvas.getContext("2d");
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, W, H);
      const v = V(), c0 = Math.exp(v.x0), c1 = Math.exp(v.x1);
      ctx.strokeStyle = U.css("--grid");
      ctx.fillStyle = U.css("--ink-2");
      ctx.font = "11px " + U.css("--font");
      ctx.lineWidth = 1;
      const steps = Math.log10(c1 / c0) > 3 ? [1] : [1, 2, 5];
      let ticks = [];
      for (let e = Math.floor(Math.log10(c0)); e <= Math.ceil(Math.log10(c1)); e++)
        for (const m of steps) if (m * 10 ** e >= c0 && m * 10 ** e <= c1) ticks.push(m * 10 ** e);
      if (ticks.length < 3) { ticks = []; for (let k = 1; k <= 5; k++) ticks.push(+Math.exp(v.x0 + ((v.x1 - v.x0) * k) / 6).toPrecision(2)); }
      for (const c of ticks) { const X = sx(c); ctx.beginPath(); ctx.moveTo(X, M.t); ctx.lineTo(X, H - M.b); ctx.stroke(); ctx.fillText(U.moneyShort(c), X - 14, H - M.b + 14); }
      const span = v.y1 - v.y0, dec = span < 0.02 ? 4 : span < 0.2 ? 3 : 2;
      for (let k = 0; k <= 5; k++) { const u = v.y0 + (span * k) / 5, Y = sy(u); ctx.beginPath(); ctx.moveTo(M.l, Y); ctx.lineTo(W - M.r, Y); ctx.stroke(); ctx.fillText(u.toFixed(dec), 4, Y + 4); }
      ctx.fillText("fleet cost (log scale)", W / 2 - 40, H - 8);
      ctx.fillText("MAU", 8, 12);
      ctx.save();
      ctx.beginPath(); ctx.rect(M.l, M.t, W - M.l - M.r, H - M.t - M.b); ctx.clip();
      if (pts) {
        // mixed first (smaller, fainter), then road-only and bike-only on top, as on the explorer
        for (const t of ["mixed", "road-only", "bike-only"]) {
          const r = t === "mixed" ? 3 : 4;
          ctx.globalAlpha = t === "mixed" ? 0.45 : 0.85;
          ctx.fillStyle = U.typeColor(t);
          ctx.beginPath();
          pts.x.forEach((c, i) => {
            if (!visible[i] || pts.t[i] !== t || c < c0 || c > c1) return;
            shape(ctx, t, sx(c), sy(pts.y[i]), r);
          });
          ctx.fill();
        }
        ctx.globalAlpha = 1;
      }
      for (const s of series) {
        ctx.strokeStyle = s.color;
        ctx.globalAlpha = filteredFront ? 0.35 : 1;
        ctx.lineWidth = 2;
        ctx.setLineDash(s.dash || []);
        stepLine(ctx, s.front.map((p) => p.fleet_cost_usd), s.front.map((p) => p.mau));
        ctx.setLineDash([]);
        // The front's own points, larger and outlined so they stand out from the cloud.
        ctx.lineWidth = 1.5;
        ctx.strokeStyle = U.css("--surface");
        for (const p of s.front) {
          if (p.fleet_cost_usd < c0 || p.fleet_cost_usd > c1) continue;
          ctx.fillStyle = series.length > 1 ? s.color : U.typeColor(p.fleet_type);
          ctx.beginPath();
          shape(ctx, p.fleet_type, sx(p.fleet_cost_usd), sy(p.mau), 5.5);
          ctx.fill();
          ctx.stroke();
        }
        ctx.globalAlpha = 1;
      }
      if (filteredFront) {
        ctx.strokeStyle = U.css("--ink");
        ctx.lineWidth = 2;
        ctx.setLineDash([6, 4]);
        stepLine(ctx, filteredFront.map((i) => pts.x[i]), filteredFront.map((i) => pts.y[i]));
        ctx.setLineDash([]);
      }
      for (const m of markers || []) {
        const X = sx(m.fleet_cost_usd), Y = sy(m.mau);
        ctx.fillStyle = m.role === "reference" ? U.css("--bad") : U.css("--ink");
        ctx.strokeStyle = U.css("--surface");
        ctx.lineWidth = 1.5;
        ctx.beginPath(); ctx.moveTo(X, Y - 9); ctx.lineTo(X + 9, Y); ctx.lineTo(X, Y + 9); ctx.lineTo(X - 9, Y); ctx.closePath(); ctx.fill(); ctx.stroke();
        ctx.fillStyle = U.css("--ink");
        ctx.font = "600 11.5px " + U.css("--font");
        ctx.fillText(m.role === "reference" ? "reference" : m.architecture.split(" (")[0], X + 12, Y - 8);
        ctx.font = "11px " + U.css("--font");
      }
      for (const t of tags) {
        if (t.mau === undefined) continue;
        const X = sx(t.fleet_cost_usd), Y = sy(t.mau);
        ctx.fillStyle = U.css("--star");
        ctx.strokeStyle = U.css("--surface");
        ctx.lineWidth = 1.5;
        star(ctx, X, Y, 12); ctx.fill(); ctx.stroke();
        ctx.fillStyle = U.css("--ink");
        ctx.font = "600 12px " + U.css("--font");
        ctx.fillText(t.label, X + 14, Y + 4);
        ctx.font = "11px " + U.css("--font");
      }
      if (picked) {
        ctx.strokeStyle = U.css("--ink");
        ctx.lineWidth = 2;
        ctx.beginPath(); ctx.arc(sx(picked.x), sy(picked.y), 10, 0, 2 * Math.PI); ctx.stroke();
      }
      ctx.restore();
    }

    function showDetails(item) {
      picked = item;
      draw();
      details.textContent = "";
      if (!item) return (details.hidden = true);
      details.hidden = false;
      const id = U.archId(item.arch);
      const tagged = state.tags.find((t) => t.id === id);
      const fmt = (v, d) => (v === null || v === undefined ? "–" : (+v).toFixed(d));
      details.append(
        U.el("div", { class: "grow" }, [U.el("b", { text: id }), U.el("div", { class: "muted small", text: (item.where ? item.where + " · " : "") + U.money(item.x) + " · MAU " + item.y.toFixed(3) + " · wait " + fmt(item.wait, 1) + " min · availability " + fmt(item.avail, 3) + " · travel " + fmt(item.travel, 1) + " min" })]),
        tagged ? U.el("button", { type: "button", class: "chip", text: "★ Untag “" + tagged.label + "”", onclick: () => removeTag(id) })
          : U.el("button", { type: "button", class: "chip primary", text: "☆ Tag this architecture", onclick: () => addTag(id) }),
        U.el("button", { type: "button", class: "chip", text: "Close", onclick: () => showDetails(null) }),
      );
    }

    legend.append(...series.map((s) => U.el("span", null, [U.el("span", { class: "sw", style: "background:" + s.color }), s.label + " front (" + s.front.length + ")"])));
    if (pts) legend.append(...U.TYPES.map((t) => U.el("span", null, [U.shapeSvg(U.typeShape(t), U.typeColor(t), 12), " " + t])), U.el("span", { class: "muted", text: "(large outlined = on the Pareto front)" }));
    if (markers && markers.length) legend.append(U.el("span", { text: "◆ reference (red) and anchors" }));
    if (tags.some((t) => t.mau !== undefined)) legend.append(U.el("span", { text: "★ tagged" }));

    const tip = $("tip");
    const local = (e) => { const r = canvas.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
    function nearest(x, y) {
      const c0 = Math.exp(V().x0), c1 = Math.exp(V().x1);
      let best = null, bd = 100;
      for (const h of hoverItems()) {
        if (h.x < c0 || h.x > c1 || h.y < V().y0 || h.y > V().y1) continue;
        const d = (sx(h.x) - x) ** 2 + (sy(h.y) - y) ** 2;
        if (d < bd) (bd = d), (best = h);
      }
      return best;
    }
    let drag = null;
    canvas.addEventListener("pointerdown", (e) => { const [x, y] = local(e); drag = { x, y, v: Object.assign({}, V()), moved: false }; canvas.setPointerCapture(e.pointerId); });
    canvas.addEventListener("pointermove", (e) => {
      const [x, y] = local(e);
      if (drag) {
        const dx = x - drag.x, dy = y - drag.y;
        if (Math.abs(dx) + Math.abs(dy) > 3) drag.moved = true;
        if (drag.moved) {
          canvas.classList.add("dragging");
          const v = drag.v, kx = (v.x1 - v.x0) / (W - M.l - M.r), ky = (v.y1 - v.y0) / (H - M.t - M.b);
          view = { x0: v.x0 - dx * kx, x1: v.x1 - dx * kx, y0: v.y0 + dy * ky, y1: v.y1 + dy * ky };
          tip.hidden = true;
          draw();
          return;
        }
      }
      const h = nearest(x, y);
      if (!h) return (tip.hidden = true);
      tip.hidden = false;
      tip.textContent = (h.where ? h.where + ": " : "") + U.archId(h.arch) + " · " + U.money(h.x) + " · MAU " + h.y.toFixed(3) + " (click to select)";
      tip.style.left = e.pageX + 12 + "px";
      tip.style.top = e.pageY + 12 + "px";
    });
    canvas.addEventListener("pointerup", (e) => {
      canvas.classList.remove("dragging");
      if (drag && !drag.moved) { const [x, y] = local(e); showDetails(nearest(x, y)); }
      drag = null;
    });
    canvas.addEventListener("pointercancel", () => { canvas.classList.remove("dragging"); drag = null; });
    canvas.addEventListener("pointerleave", () => (tip.hidden = true));
    canvas.addEventListener("dblclick", () => { view = null; draw(); });
    canvas.addEventListener("wheel", (e) => {
      e.preventDefault();
      const [x, y] = local(e);
      const k = Math.exp(Math.max(-0.5, Math.min(0.5, e.deltaY * 0.0015)));
      const v = V(), cx = invX(x), cy = invY(y);
      view = { x0: cx - (cx - v.x0) * k, x1: cx + (v.x1 - cx) * k, y0: cy - (cy - v.y0) * k, y1: cy + (v.y1 - cy) * k };
      tip.hidden = true;
      draw();
    }, { passive: false });

    if (opts.filters && pts) wrap.append(filterPanel());
    wrap.append(U.el("div", { class: "lab-row" }, [zoom, reset, U.el("span", { class: "muted small", text: "Drag to pan · scroll to zoom · double-click to reset · click a point to select or tag it" })]), canvas, legend);
    if (pts) wrap.append(countLine);
    wrap.append(details);
    requestAnimationFrame(() => (pts ? applyFilters() : draw()));
    new ResizeObserver(() => draw()).observe(canvas);
    wrap.select = (arch) => { const h = hoverItems().find((x) => sameArch(x.arch, arch)); if (h) showDetails(h); };
    return wrap;
  }

  // ---------- tags: architectures to highlight in every run ----------
  state.tags = load("os4lab.tags", []);
  function saveTags() {
    store("os4lab.tags", state.tags);
    if (state.result) calculate(); // re-score the tags under the current inputs (the run itself comes from the cache)
  }
  function addTag(id, label) {
    if (!id || state.tags.some((t) => t.id === id)) return;
    label = label || prompt("Label for this architecture:", "tag " + (state.tags.length + 1));
    if (label === null) return;
    state.tags.push({ id, label: label || id });
    saveTags();
  }
  function removeTag(id) {
    state.tags = state.tags.filter((t) => t.id !== id);
    saveTags();
  }
  function tagsSection(rows) {
    const box = U.el("div");
    const idIn = U.el("input", { type: "text", placeholder: "e.g. 2×C8-P1-G3-M4-A3 + 20×B1-E1-G2-K1", style: "width:24em", "aria-label": "architecture id" });
    const labelIn = U.el("input", { type: "text", placeholder: "label", style: "width:9em", "aria-label": "tag label" });
    box.append(U.el("p", { class: "muted small", text: "Tagged architectures are kept in this browser and scored in every run, under that run's inputs, whether or not they are on the chart. Click a point or a table row to tag it, or type its id." }),
      U.el("div", { class: "lab-row" }, [idIn, labelIn, U.el("button", { type: "button", class: "chip", text: "Add tag", onclick: () => { const id = idIn.value.trim().replace(/\s*[x*]\s*/g, "×"); if (id) addTag(id, labelIn.value.trim() || id); } })]));
    if (!rows.length) return box.append(U.el("p", { class: "muted", text: "No tags yet." })), box;
    const t = U.el("div");
    box.append(t);
    U.Table(t, {
      rows: () => rows,
      columns: [
        { key: "label", label: "tag" }, { key: "id", label: "architecture" },
        { key: "fleet_cost_usd", label: "cost", num: true }, { key: "mau", label: "MAU", num: true }, { key: "wait_time", label: "wait (min)", num: true },
        { key: "availability", label: "availability", num: true }, { key: "travel_time", label: "travel (min)", num: true },
        { key: "dominated", label: "dominated by the front" }, { key: "status", label: "status" },
        { key: "remove", label: "", render: (_, r) => U.el("button", { type: "button", class: "chip", text: "Remove", onclick: (e) => { e.stopPropagation(); removeTag(r.id); } }) },
      ],
    });
    return box;
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
    return { id: r.key + "-" + Date.now().toString(36), name: r.name, savedAt: new Date().toISOString(), config: r.config, summary: r.summary, front: r.front, notes: r.notes, tags: r.tags || [] };
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
    const tagIds = Array.from(new Set(runs.flatMap((r) => (r.tags || []).map((t) => t.id))));
    if (tagIds.length) {
      const cell = (r, id) => {
        const t = (r.tags || []).find((x) => x.id === id);
        if (!t) return "not tagged when saved";
        if (t.mau === undefined) return t.status;
        return "MAU " + t.mau.toFixed(3) + " · " + U.money(t.fleet_cost_usd) + (t.dominated ? " · dominated" : "") + (t.status !== "ok" ? " · " + t.status : "");
      };
      const label = (id) => { for (const r of runs) { const t = (r.tags || []).find((x) => x.id === id); if (t) return t.label + " (" + id + ")"; } return id; };
      out.append(U.el("h2", { text: "Tagged architectures across runs" }), simpleTable(["tag", ...runs.map((r) => r.name)], tagIds.map((id) => [label(id), ...runs.map((r) => cell(r, id))])));
    }
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

  let started = false;
  async function init() {
    try {
      const session = await api("/api/session");
      if (session.auth_required && !session.ok) return showLogin();
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
    $("limit").checked = state.limit;
    $("limit-label").textContent = "limit runs to " + millions(state.schema.limits.default) + " architectures";
    scheduleEstimate();
    if (started) return;
    started = true;
    $("limit").addEventListener("change", (e) => { state.limit = e.target.checked; store("os4lab.limit", state.limit); scheduleEstimate(); if ($("auto").checked) scheduleCalc(); });
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
