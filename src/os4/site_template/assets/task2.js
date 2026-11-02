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
  const hState = { q: "", kind: "", type: "" };
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
  hf.append(
    el("label", { class: "f" }, [el("span", { text: "search" }), (() => {
      const i = el("input", { type: "search", placeholder: "variant, reason…" });
      i.addEventListener("input", () => { hState.q = i.value.toLowerCase(); hTable.update(); });
      return i;
    })()]),
    el("label", { class: "f" }, [el("span", { text: "reason" }), mkSelect(kinds, (v) => { hState.kind = v; hTable.update(); })]),
    el("label", { class: "f" }, [el("span", { text: "fleet type" }), mkSelect(types.map((t) => [t, t || "any"]), (v) => { hState.type = v; hTable.update(); })])
  );
  const hTable = U.Table(document.getElementById("highlights"), {
    columns: archColumns(H),
    rows: () =>
      H.filter(
        (r) =>
          (!hState.kind || r.reason.includes(hState.kind)) &&
          (!hState.type || r.fleet_type === hState.type) &&
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
  const vState = { q: "", kind: "", chassis: "", kept: false, spares: "" };
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
