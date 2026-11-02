(function () {
  "use strict";
  const U = OS4.util;
  const el = U.el;
  U.header("task2.html");
  const T = OS4.task2;
  if (!T) return;

  const LEAD = ["architecture", "id", "case", "reason", "fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_cost_usd", "mau", "mau_os3a_extended", "mau_os3a_full"];
  const HIDE = ["road_chassis", "bike_frame"]; // shown via the variant ids
  function orderedKeys(rows) {
    const keys = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!keys.includes(k)) keys.push(k);
    return LEAD.filter((k) => keys.includes(k)).concat(keys.filter((k) => !LEAD.includes(k)));
  }
  function archColumns(rows, skip) {
    return U.columnsFor(orderedKeys(rows), HIDE.concat(skip || [])).map((c) => (c.key === "reason" ? Object.assign(c, { cls: "wrap-text" }) : c));
  }

  // ----- five architectures -----
  U.Table(document.getElementById("archs"), {
    columns: archColumns(T.architectures),
    rows: () => T.architectures,
    id: (r) => r.id,
    record: (r) => r,
    source: "Task 2 architecture",
  });

  // ----- highlights -----
  const H = T.highlights;
  document.getElementById("hl-note").textContent =
    H.length +
    " architectures picked from both battery cases: the cheapest threshold-meeting fleet for each road chassis and each bike frame (fixed and removable batteries), each case's Pareto knee (first front point with MAU ≥ 0.94), evenly spaced Pareto points, and the mixed fleets with the highest MAU per dollar. Duplicates are merged; the reason column lists every reason and case.";
  const hf = document.getElementById("hl-filters");
  const hState = { q: "", kind: "", type: "", case: "", road_chassis: "", bike_frame: "", battery: "",
    n_road: [null, null], n_bike: [null, null], cost: [null, null], minU: null, flags: new Set() };
  const kinds = [
    ["", "any reason"],
    ["cheapest road-only", "cheapest per road chassis"],
    ["cheapest bike-only", "cheapest per bike frame"],
    ["Pareto knee", "Pareto knee"],
    ["Pareto front point", "evenly spaced Pareto points"],
    ["MAU per dollar", "best MAU per dollar (mixed)"],
  ];
  const types = ["", "road-only", "bike-only", "mixed"];
  const mkSelect = (opts, onchange) => {
    const s = el("select", null, opts.map(([v, t]) => el("option", { value: v, text: t })));
    s.addEventListener("change", () => onchange(s.value));
    return s;
  };
  const numInput = (placeholder, onchange, step) => {
    const i = el("input", { type: "number", placeholder, step: step || "any", min: "0" });
    i.addEventListener("input", () => onchange(i.value === "" ? null : +i.value));
    return i;
  };
  // A min–max pair of number inputs that writes into range[0] / range[1] (times scale).
  const rangeFilter = (label, range, step, scale, onchange) =>
    el("div", { class: "f" }, [el("span", { text: label }), el("div", { class: "range" }, [
      numInput("min", (v) => { range[0] = v === null ? null : v * (scale || 1); onchange(); }, step), "–",
      numInput("max", (v) => { range[1] = v === null ? null : v * (scale || 1); onchange(); }, step),
    ])]);
  const inRange = (v, [lo, hi]) => (lo === null || v >= lo) && (hi === null || v <= hi);
  const distinct = (rows, k) => [...new Set(rows.map((r) => r[k]).filter((v) => v !== null && v !== undefined && v !== ""))].sort();
  const anyOpts = (vals) => [["", "any"]].concat(vals.map((v) => [v, v]));
  hf.append(
    el("label", { class: "f" }, [el("span", { text: "search" }), (() => {
      const i = el("input", { type: "search", placeholder: "variant, reason…" });
      i.addEventListener("input", () => { hState.q = i.value.toLowerCase(); hTable.update(); });
      return i;
    })()]),
    el("label", { class: "f" }, [el("span", { text: "reason" }), mkSelect(kinds, (v) => { hState.kind = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "fleet type" }), mkSelect(types.map((t) => [t, t || "any"]), (v) => { hState.type = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "battery case" }), mkSelect(anyOpts([...new Set(H.flatMap((r) => r.case.split(", ")))].sort()), (v) => { hState.case = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "road chassis" }), mkSelect(anyOpts(distinct(H, "road_chassis")), (v) => { hState.road_chassis = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "bike frame" }), mkSelect(anyOpts(distinct(H, "bike_frame")), (v) => { hState.bike_frame = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "bike battery" }), mkSelect(anyOpts(distinct(H, "battery")), (v) => { hState.battery = v; hTable.update(); })]),
    rangeFilter("N road", hState.n_road, "1", 1, () => hTable.update()),
    rangeFilter("N bike", hState.n_bike, "5", 1, () => hTable.update()),
    rangeFilter("cost ($M)", hState.cost, "0.1", 1e6, () => hTable.update()),
    el("label", { class: "f" }, [el("span", { text: "min MAU" }), numInput("e.g. 0.9", (v) => { hState.minU = v; hTable.update(); }, "0.01")]),
    el("div", { class: "f" }, [el("span", { text: "only architectures meeting" }), el("div", { class: "range" },
      Object.keys(H[0] || {}).filter((k) => k.startsWith("meets_")).map((k) => el("label", { class: "chk" }, [(() => {
        const c = el("input", { type: "checkbox" });
        c.addEventListener("change", () => { c.checked ? hState.flags.add(k) : hState.flags.delete(k); hTable.update(); });
        return c;
      })(), U.label(k).replace(/^meets /, "")])))])
  );
  const hTable = U.Table(document.getElementById("highlights"), {
    columns: archColumns(H),
    rows: () =>
      H.filter(
        (r) =>
          (!hState.kind || r.reason.includes(hState.kind)) &&
          (!hState.type || r.fleet_type === hState.type) &&
          (!hState.case || r.case.includes(hState.case)) &&
          ["road_chassis", "bike_frame", "battery"].every((k) => !hState[k] || r[k] === hState[k]) &&
          inRange(r.n_road, hState.n_road) &&
          inRange(r.n_bike, hState.n_bike) &&
          inRange(r.fleet_cost_usd, hState.cost) &&
          (hState.minU === null || r.mau >= hState.minU) &&
          [...hState.flags].every((k) => r[k]) &&
          (!hState.q || (r.id + " " + r.reason).toLowerCase().includes(hState.q))
      ),
    id: (r) => r.id,
    record: (r) => r,
    source: "Task 2 highlight",
    sort: { key: "fleet_cost_usd", dir: 1 },
  });

  // ----- variants -----
  const V = U.Columnar(T.variants);
  const vf = document.getElementById("var-filters");
  const vState = { q: "", kind: "", chassis: "", kept: false, spares: "", battery: "", charger: "", motor: "", autonomy: "",
    pax: [null, null], cost: [null, null], minAvail: null, capped: false };
  const kept = V.has("kept_after_pruning") ? Array.from({ length: V.n }, (_, i) => V.get(i, "kept_after_pruning")).filter(Boolean).length : null;
  document.getElementById("var-note").textContent =
    V.n.toLocaleString() +
    " feasible vehicle variants from vehicle.all_variants (removable-battery case, so spare-pack options are included)" +
    (kept !== null ? "; " + kept + " survive pruning of dominated variants and enter the tradespace." : ".");
  const chassisOpts = [["", "any"]].concat(V.has("chassis") ? V.dict("chassis").map((c) => [c, c]) : []);
  vf.append(
    el("label", { class: "f" }, [el("span", { text: "search id" }), (() => {
      const i = el("input", { type: "search", placeholder: "e.g. C2-P2 or S1.5" });
      i.addEventListener("input", () => { vState.q = i.value.toUpperCase(); vTable.update(); });
      return i;
    })()]),
    el("label", { class: "f" }, [el("span", { text: "kind" }), mkSelect([["", "any"], ["road", "road"], ["bike", "bike"]], (v) => { vState.kind = v; vTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "chassis / frame" }), mkSelect(chassisOpts, (v) => { vState.chassis = v; vTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "bike battery" }), mkSelect([["", "any"], ["fixed", "fixed"], ["removable", "removable (spares)"]], (v) => { vState.spares = v; vTable.update(); })]),
    ...[["battery", "battery pack"], ["charger", "charger"], ["motor", "motor"], ["autonomy", "autonomy"]].filter(([k]) => V.has(k)).map(([k, label]) =>
      el("label", { class: "f" }, [el("span", { text: label }), mkSelect(anyOpts(V.dict(k).filter((v) => v !== null && v !== "")), (v) => { vState[k] = v; vTable.update(); })])),
    rangeFilter("seats", vState.pax, "1", 1, () => vTable.update()),
    rangeFilter("cost ($k)", vState.cost, "1", 1e3, () => vTable.update()),
    el("label", { class: "f" }, [el("span", { text: "min availability" }), numInput("e.g. 0.75", (v) => { vState.minAvail = v; vTable.update(); }, "0.05")]),
    el("label", { class: "chk" }, [(() => {
      const c = el("input", { type: "checkbox" });
      c.addEventListener("change", () => { vState.capped = c.checked; vTable.update(); });
      return c;
    })(), "only variants at the speed cap"]),
    V.has("kept_after_pruning")
      ? el("label", { class: "chk" }, [(() => {
          const c = el("input", { type: "checkbox" });
          c.addEventListener("change", () => { vState.kept = c.checked; vTable.update(); });
          return c;
        })(), "only variants kept after pruning"])
      : null
  );
  const all = Array.from({ length: V.n }, (_, i) => i);
  const vTable = U.Table(document.getElementById("variants"), {
    columns: U.columnsFor(V.names),
    getValue: (i, k) => V.get(i, k),
    rows: () =>
      all.filter((i) => {
        if (vState.kind && V.get(i, "kind") !== vState.kind) return false;
        if (vState.chassis && V.get(i, "chassis") !== vState.chassis) return false;
        for (const k of ["battery", "charger", "motor", "autonomy"]) if (vState[k] && V.get(i, k) !== vState[k]) return false;
        if (!inRange(V.get(i, "pax"), vState.pax) || !inRange(V.get(i, "cost_usd"), vState.cost)) return false;
        if (vState.minAvail !== null && V.get(i, "availability") < vState.minAvail) return false;
        if (vState.capped && !V.get(i, "speed_capped")) return false;
        if (vState.kept && !V.get(i, "kept_after_pruning")) return false;
        if (vState.spares === "fixed" && (V.get(i, "kind") !== "bike" || V.get(i, "spares_per_bike") > 0)) return false;
        if (vState.spares === "removable" && !(V.get(i, "spares_per_bike") > 0)) return false;
        if (vState.q && !String(V.get(i, "variant_id")).includes(vState.q)) return false;
        return true;
      }),
    pageSize: 50,
  });
  U.footer();
})();
