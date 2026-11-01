(function () {
  "use strict";
  const U = OS4.util;
  const el = U.el;
  U.header("task1.html");
  const T = OS4.task1;
  if (!T) return;
  const NS = "http://www.w3.org/2000/svg";
  const CASE_SLOTS = ["--road", "--bike", "--mixed"]; // categorical slots 1-3 for cases A, B, C
  const caseColor = (i) => U.css(CASE_SLOTS[i % 3]);
  const attrLabel = {};
  for (const s of T.saus) attrLabel[s.attribute] = s.label;

  // ----- formula -----
  const w = T.weights.appendix_a;
  const formula = el("div", { class: "formula" }, ["U = "]);
  T.attributes.forEach((a, i) => {
    if (i) formula.appendChild(document.createTextNode(" + "));
    formula.appendChild(el("span", { title: attrLabel[a] }, [String(w[a]) + " · u", el("sub", { text: a.replace(/_/g, " ") })]));
  });
  document.getElementById("formula").appendChild(formula);

  // ----- cases table -----
  const caseKeys = Object.keys(T.cases[0] || {});
  U.Table(document.getElementById("cases"), {
    columns: U.columnsFor(caseKeys).map((c) => Object.assign(c, { label: c.key.startsWith("u_") ? "u(" + c.key.slice(2).replace(/_/g, " ") + ")" : c.key.startsWith("k*u_") ? "k·u(" + c.key.slice(4).replace(/_/g, " ") + ")" : U.label(c.key) })),
    rows: () => T.cases,
    sort: { key: "case", dir: 1 },
  });

  // ----- weights -----
  const attrs = Object.keys(T.weights).reduce((acc, k) => acc.concat(Object.keys(T.weights[k]).filter((a) => !acc.includes(a))), []);
  const weightRows = attrs.map((a) => {
    const r = { attribute: a, proposed: T.proposed_attributes.includes(a) ? "proposed" : "" };
    for (const set of Object.keys(T.weights)) r["weight_" + set] = T.weights[set][a] === undefined ? null : T.weights[set][a];
    return r;
  });
  U.Table(document.getElementById("weights"), {
    columns: [{ key: "attribute", label: "attribute" }, { key: "proposed", label: "status" }].concat(
      Object.keys(T.weights).map((s) => ({ key: "weight_" + s, label: "k · " + s, num: true, fmt: (v) => (v === null ? "–" : v.toFixed(2)) }))
    ),
    rows: () => weightRows,
  });
  U.Table(document.getElementById("weight-sets"), {
    columns: U.columnsFor(Object.keys(T.weight_sets[0] || {})),
    rows: () => T.weight_sets,
    sort: { key: "case", dir: 1 },
  });

  // ----- sensitivity -----
  U.Table(document.getElementById("sensitivity"), {
    columns: U.columnsFor(Object.keys(T.sensitivity[0] || {})).map((c) =>
      c.key === "delta" ? Object.assign(c, { fmt: (v) => (v > 0 ? "+" : "") + v.toFixed(2) }) : c
    ),
    rows: () => T.sensitivity,
    rowClass: (r) => (r.flipped ? "flip" : ""),
  });

  // ----- SAU curves -----
  const legend = document.getElementById("sau-legend");
  legend.appendChild(U.legendItem(U.shapeSvg("line", U.css("--ink-2")), "SAU (piecewise linear)"));
  T.cases.forEach((c, i) => legend.appendChild(U.legendItem(U.shapeSvg("circle", caseColor(i)), "Case " + c.case)));

  const grid = document.getElementById("saus");
  const charts = [];
  for (const s of T.saus) charts.push(sauChart(grid, s));
  U.onTheme(() => charts.forEach((c) => c.draw()));

  function niceTicks(lo, hi, n) {
    const span = hi - lo || 1;
    const step0 = span / n;
    const mag = Math.pow(10, Math.floor(Math.log10(step0)));
    const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0) || step0;
    const out = [];
    for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
    return out;
  }
  function interp(xs, us, x) {
    const pts = xs.map((v, i) => [v, us[i]]).sort((a, b) => a[0] - b[0]);
    if (x <= pts[0][0]) return pts[0][1];
    if (x >= pts[pts.length - 1][0]) return pts[pts.length - 1][1];
    for (let i = 1; i < pts.length; i++) {
      if (x <= pts[i][0]) {
        const [x0, u0] = pts[i - 1];
        const [x1, u1] = pts[i];
        return u0 + ((u1 - u0) * (x - x0)) / (x1 - x0);
      }
    }
    return pts[pts.length - 1][1];
  }
  function svgEl(tag, attrs) {
    const n = document.createElementNS(NS, tag);
    for (const [k, v] of Object.entries(attrs || {})) n.setAttribute(k, v);
    return n;
  }

  function sauChart(parent, s) {
    const card = el("div", { class: "sau-card" });
    const title = el("h3", null, [s.label]);
    if (s.proposed) title.appendChild(el("span", { class: "tag proposed", text: "proposed, for team review" }));
    const readout = el("div", { class: "readout", "aria-live": "polite" });
    const W = 360, H = 220, m = { l: 40, r: 14, t: 12, b: 36 };
    const svg = svgEl("svg", { viewBox: "0 0 " + W + " " + H, tabindex: "0", role: "img", "aria-label": s.label + " utility curve" });
    card.append(title, el("div", { class: "muted small", text: "x in " + s.unit }), svg, readout);
    parent.appendChild(card);
    const xmin = Math.min.apply(null, s.x), xmax = Math.max.apply(null, s.x);
    const sx = (x) => m.l + ((x - xmin) / (xmax - xmin || 1)) * (W - m.l - m.r);
    const sy = (u) => H - m.b - u * (H - m.t - m.b);
    const caseMarks = T.attributes.includes(s.attribute)
      ? T.cases.map((c, i) => ({ name: c.case, x: c[s.attribute], u: c["u_" + s.attribute], i }))
      : [];
    let hoverX = null;
    function draw() {
      svg.textContent = "";
      const ink2 = U.css("--ink-2"), gridC = U.css("--grid"), muted = U.css("--muted"), surface = U.css("--surface"), ink = U.css("--ink");
      for (const u of [0, 0.25, 0.5, 0.75, 1]) {
        svg.appendChild(svgEl("line", { x1: m.l, x2: W - m.r, y1: sy(u), y2: sy(u), stroke: gridC, "stroke-width": 1 }));
        const t = svgEl("text", { x: m.l - 6, y: sy(u) + 4, "text-anchor": "end", "font-size": 11, fill: muted });
        t.textContent = u.toFixed(2).replace(/0$/, "");
        svg.appendChild(t);
      }
      for (const x of niceTicks(xmin, xmax, 5)) {
        const t = svgEl("text", { x: sx(x), y: H - m.b + 16, "text-anchor": "middle", "font-size": 11, fill: muted });
        t.textContent = String(+x.toFixed(3));
        svg.appendChild(t);
      }
      const xl = svgEl("text", { x: (m.l + W - m.r) / 2, y: H - 4, "text-anchor": "middle", "font-size": 11, fill: ink2 });
      xl.textContent = s.unit;
      svg.appendChild(xl);
      const pts = s.x.map((x, i) => [x, s.u[i]]).sort((a, b) => a[0] - b[0]);
      svg.appendChild(
        svgEl("polyline", { points: pts.map((p) => sx(p[0]) + "," + sy(p[1])).join(" "), fill: "none", stroke: ink2, "stroke-width": 2, "stroke-linejoin": "round", "stroke-linecap": "round" })
      );
      for (const p of pts) svg.appendChild(svgEl("circle", { cx: sx(p[0]), cy: sy(p[1]), r: 3, fill: ink2, stroke: surface, "stroke-width": 1.5 }));
      for (const c of caseMarks) {
        const cx = sx(Math.min(Math.max(c.x, xmin), xmax)), cy = sy(c.u);
        svg.appendChild(svgEl("circle", { cx, cy, r: 5, fill: caseColor(c.i), stroke: surface, "stroke-width": 2 }));
        const dup = caseMarks.filter((d) => d.i < c.i && d.x === c.x).length; // same point: label side by side
        const right = cx > W - m.r - 24; // near the right edge: label to the left of the mark
        const t = svgEl("text", { x: right ? cx - 8 - dup * 10 : cx + 7 + dup * 10, y: Math.max(cy - 7, 11), "text-anchor": right ? "end" : "start", "font-size": 11, "font-weight": 600, fill: ink });
        t.textContent = c.name;
        svg.appendChild(t);
      }
      if (hoverX !== null) {
        const u = interp(s.x, s.u, hoverX);
        svg.appendChild(svgEl("line", { x1: sx(hoverX), x2: sx(hoverX), y1: m.t, y2: H - m.b, stroke: muted, "stroke-width": 1 }));
        svg.appendChild(svgEl("circle", { cx: sx(hoverX), cy: sy(u), r: 4.5, fill: ink, stroke: surface, "stroke-width": 2 }));
      }
    }
    function setX(x) {
      hoverX = Math.min(Math.max(x, xmin), xmax);
      const u = interp(s.x, s.u, hoverX);
      readout.textContent = "";
      readout.append("x = ", el("b", { text: String(+hoverX.toPrecision(4)) }), " " + s.unit + " → u = ", el("b", { text: u.toFixed(3) }));
      draw();
    }
    function caseText() {
      readout.textContent = caseMarks.length
        ? caseMarks.map((c) => c.name + ": x = " + c.x + ", u = " + c.u.toFixed(3)).join(" · ")
        : "Breakpoints: " + s.x.map((x, i) => "(" + x + ", " + s.u[i] + ")").join(" ");
    }
    svg.addEventListener("pointermove", (e) => {
      const r = svg.getBoundingClientRect();
      const px = ((e.clientX - r.left) / r.width) * W;
      setX(xmin + ((px - m.l) / (W - m.l - m.r)) * (xmax - xmin));
    });
    svg.addEventListener("pointerleave", () => {
      hoverX = null;
      caseText();
      draw();
    });
    svg.addEventListener("keydown", (e) => {
      const step = (xmax - xmin) / 100;
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
        e.preventDefault();
        setX((hoverX === null ? xmin : hoverX) + (e.key === "ArrowRight" ? step : -step));
      }
    });
    svg.addEventListener("blur", () => {
      hoverX = null;
      caseText();
      draw();
    });
    caseText();
    draw();
    return { draw };
  }
  U.footer();
})();
