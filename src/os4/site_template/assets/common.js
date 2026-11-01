/* Shared helpers for the OS4 explorer: navigation, formatting, selection store, tables. No dependencies. */
(function () {
  "use strict";
  const OS4 = (window.OS4 = window.OS4 || {});
  const U = (OS4.util = {});

  // ---------- DOM ----------
  U.el = function (tag, attrs, children) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const [k, v] of Object.entries(attrs)) {
        if (v === undefined || v === null || v === false) continue;
        if (k === "text") node.textContent = v;
        else if (k === "class") node.className = v;
        else if (k.startsWith("on")) node.addEventListener(k.slice(2), v);
        else node.setAttribute(k, v === true ? "" : v);
      }
    }
    for (const c of [].concat(children || [])) {
      if (c === null || c === undefined || c === false) continue;
      node.appendChild(typeof c === "string" || typeof c === "number" ? document.createTextNode(String(c)) : c);
    }
    return node;
  };
  U.css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  U.ramp = () => U.css("--ramp").split(",").map((s) => s.trim());
  U.TYPES = ["road-only", "bike-only", "mixed"];
  U.typeColor = (t) => U.css(t === "road-only" ? "--road" : t === "bike-only" ? "--bike" : "--mixed");
  U.typeShape = (t) => (t === "road-only" ? "circle" : t === "bike-only" ? "triangle" : "square");

  // ---------- formatting ----------
  const labels = () => (OS4.meta && OS4.meta.labels) || {};
  U.label = (key) => labels()[key] || key.replace(/_/g, " ");
  U.isMoney = (key) => /(_usd|cost)$/.test(key) || key.endsWith("_usd");
  U.isUnit = (key) => /^(mau|u_|k\*u_)|availability|bike_share|^weight$/.test(key);
  const nf0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
  const nf1 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 1 });
  const nf2 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 2 });
  U.money = (v) => (v === null || v === undefined || Number.isNaN(v) ? "–" : "$" + nf0.format(v));
  U.moneyShort = function (v) {
    const a = Math.abs(v);
    if (a >= 1e6) return "$" + (+(v / 1e6).toPrecision(3)) + "M";
    if (a >= 1e3) return "$" + (+(v / 1e3).toPrecision(3)) + "K";
    return "$" + nf0.format(v);
  };
  U.fmt = function (key, v) {
    if (v === null || v === undefined || v === "" || (typeof v === "number" && Number.isNaN(v))) return "–";
    if (typeof v === "boolean") return v ? "yes" : "no";
    if (typeof v !== "number") return String(v);
    if (U.isMoney(key)) return U.money(v);
    if (U.isUnit(key)) return v.toFixed(3);
    if (Number.isInteger(v)) return nf0.format(v);
    if (Math.abs(v) >= 100) return nf0.format(v);
    if (Math.abs(v) >= 10) return nf1.format(v);
    return nf2.format(v);
  };
  U.isBoolKey = (key) => /^meets_|^flipped$|^kept_|_capped$/.test(key);

  // ---------- architecture ids (same string as os4.site.arch_id) ----------
  U.archId = function (r) {
    const parts = [];
    if (r.n_road > 0) parts.push(r.n_road + "×" + r.road_variant);
    if (r.n_bike > 0) parts.push(r.n_bike + "×" + r.bike_variant);
    return parts.join(" + ");
  };

  // ---------- columnar tables from site.py ----------
  U.Columnar = function (t) {
    const kinds = {};
    for (const c of t.columns) kinds[c.name] = c.kind;
    const self = {
      n: t.n,
      columns: t.columns,
      names: t.columns.map((c) => c.name),
      has: (name) => name in kinds,
      kind: (name) => kinds[name],
      raw: (i, name) => t.data[name][i],
      dict: (name) => t.dicts[name] || [],
      get(i, name) {
        const v = t.data[name] ? t.data[name][i] : undefined;
        const k = kinds[name];
        if (k === "cat") return v < 0 ? null : t.dicts[name][v];
        if (k === "bool") return v === 1;
        return v;
      },
      record(i) {
        const r = {};
        for (const name of self.names) r[name] = self.get(i, name);
        return r;
      },
    };
    return self;
  };

  // ---------- selection store (localStorage, falls back to memory) ----------
  const KEY = "os4.selection.v1";
  let memory = {};
  let storageOk = true;
  function read() {
    try {
      const raw = window.localStorage.getItem(KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (e) {
      storageOk = false;
      return memory;
    }
  }
  function write(obj) {
    memory = obj;
    try {
      window.localStorage.setItem(KEY, JSON.stringify(obj));
    } catch (e) {
      storageOk = false;
    }
    listeners.forEach((fn) => fn());
  }
  const listeners = [];
  const Sel = (OS4.selection = {
    all: () => read(),
    has: (id) => Object.prototype.hasOwnProperty.call(read(), id),
    count: () => Object.keys(read()).length,
    add(id, record, source) {
      const s = read();
      s[id] = { id, source: source || "", saved: new Date().toISOString(), record: record || {} };
      write(s);
    },
    remove(id) {
      const s = read();
      delete s[id];
      write(s);
    },
    toggle(id, record, source) {
      if (Sel.has(id)) Sel.remove(id);
      else Sel.add(id, record, source);
      return Sel.has(id);
    },
    clear: () => write({}),
    onChange: (fn) => listeners.push(fn),
    persistent: () => storageOk,
  });
  window.addEventListener("storage", (e) => {
    if (e.key === KEY) listeners.forEach((fn) => fn());
  });

  U.starButton = function (id, getRecord, source) {
    const b = U.el("button", { class: "star", type: "button", title: "Select / unselect this architecture" });
    const sync = () => {
      const on = Sel.has(id);
      b.textContent = on ? "★" : "☆";
      b.setAttribute("aria-pressed", on ? "true" : "false");
      b.setAttribute("aria-label", (on ? "Unselect " : "Select ") + id);
    };
    b.addEventListener("click", (e) => {
      e.stopPropagation();
      Sel.toggle(id, getRecord(), source);
    });
    sync();
    b._sync = sync;
    return b;
  };

  // ---------- CSV ----------
  U.csv = function (rows, columns) {
    const esc = (v) => {
      if (v === null || v === undefined) return "";
      const s = String(v);
      return /[",\n\r]/.test(s) ? '"' + s.replace(/"/g, '""') + '"' : s;
    };
    return [columns.map(esc).join(",")].concat(rows.map((r) => columns.map((c) => esc(r[c])).join(","))).join("\r\n");
  };
  U.selectionCsv = function () {
    const items = Object.values(Sel.all());
    const cols = ["id", "source", "saved"];
    for (const it of items) for (const k of Object.keys(it.record || {})) if (!cols.includes(k)) cols.push(k);
    const rows = items.map((it) => Object.assign({}, it.record, { id: it.id, source: it.source, saved: it.saved }));
    return U.csv(rows, cols);
  };
  // A real <a download> link whose href is a Blob URL, refreshed whenever the selection changes.
  U.exportLink = function (text) {
    const a = U.el("a", { class: "export", download: "os4_selected_architectures.csv", text: text || "Export CSV" });
    let url = null;
    const refresh = () => {
      if (url) URL.revokeObjectURL(url);
      url = URL.createObjectURL(new Blob(["﻿" + U.selectionCsv()], { type: "text/csv;charset=utf-8" }));
      a.href = url;
      a.textContent = (text || "Export CSV") + " (" + Sel.count() + ")";
    };
    refresh();
    Sel.onChange(refresh);
    return a;
  };

  // ---------- header ----------
  const PAGES = [
    ["index.html", "Overview"],
    ["task1.html", "Task 1 · Utility"],
    ["task2.html", "Task 2 · Model"],
    ["task3.html", "Task 3 · Tradespace"],
  ];
  U.header = function (current) {
    const nav = U.el("nav", { "aria-label": "Pages" }, [U.el("a", { class: "brand", href: "index.html", text: "OS4 explorer" })]);
    for (const [href, text] of PAGES) {
      nav.appendChild(U.el("a", { class: "nav", href, text, "aria-current": href === current ? "page" : null }));
    }
    nav.appendChild(U.el("span", { class: "spacer" }));
    const badge = U.el("span", { class: "badge", text: String(Sel.count()) });
    nav.appendChild(
      U.el("a", { class: "nav", href: "selected.html", "aria-current": current === "selected.html" ? "page" : null }, [
        "★ Selected ",
        badge,
      ])
    );
    Sel.onChange(() => (badge.textContent = String(Sel.count())));
    const bar = U.el("header", { class: "topbar" }, [nav]);
    document.body.insertBefore(bar, document.body.firstChild);
    if (!OS4.meta) {
      const msg = U.el("div", { class: "banner error wrap" }, [
        "Data files not found. Run ",
        U.el("code", { text: "uv run python -m os4" }),
        " and open outputs/site/index.html.",
      ]);
      bar.after(msg);
    }
  };
  U.footer = function () {
    const m = OS4.meta || {};
    const f = U.el("p", { class: "muted small wrap" }, [
      "Generated " + (m.generated || "?") + " by ",
      U.el("code", { text: "python -m os4" }),
      " · scenario: " + (m.scenario || "?"),
    ]);
    document.body.appendChild(f);
  };

  // ---------- sortable, paged table ----------
  // opts: columns [{key, label, num, fmt(v,ref), cls}], getValue(ref,key), rows(): refs,
  //       id(ref) -> selection id, record(ref) -> snapshot, source, pageSize, onRowClick(ref), sort {key, dir}
  U.Table = function (container, opts) {
    const pageSize = opts.pageSize || 50;
    let sortKey = opts.sort ? opts.sort.key : null;
    let sortDir = opts.sort ? opts.sort.dir : 1;
    let page = 0;
    let refs = [];
    let activeRef = null;
    const wrap = U.el("div", { class: "table-wrap" });
    const table = U.el("table");
    const thead = U.el("thead");
    const tbody = U.el("tbody");
    table.append(thead, tbody);
    wrap.appendChild(table);
    const pager = U.el("div", { class: "pager" });
    container.append(wrap, pager);
    const get = opts.getValue || ((r, k) => r[k]);

    function header() {
      thead.textContent = "";
      const tr = U.el("tr");
      if (opts.id) tr.appendChild(U.el("th", { title: "Select", text: "★" }));
      for (const c of opts.columns) {
        const th = U.el("th", { class: "sortable" + (c.num ? " num" : ""), scope: "col", tabindex: "0", title: "Sort by " + c.label });
        th.appendChild(document.createTextNode(c.label));
        if (c.key === sortKey) th.appendChild(U.el("span", { class: "arrow", text: sortDir > 0 ? " ▲" : " ▼" }));
        const act = () => {
          if (sortKey === c.key) sortDir = -sortDir;
          else {
            sortKey = c.key;
            sortDir = c.num ? -1 : 1;
          }
          page = 0;
          sortRefs();
          render();
        };
        th.addEventListener("click", act);
        th.addEventListener("keydown", (e) => (e.key === "Enter" || e.key === " ") && (e.preventDefault(), act()));
        tr.appendChild(th);
      }
      thead.appendChild(tr);
    }
    function sortRefs() {
      if (!sortKey) return;
      const k = sortKey;
      const d = sortDir;
      const vals = new Map();
      for (const r of refs) vals.set(r, get(r, k));
      refs.sort((a, b) => {
        const x = vals.get(a);
        const y = vals.get(b);
        if (x === y) return 0;
        if (x === null || x === undefined) return 1;
        if (y === null || y === undefined) return -1;
        return (x < y ? -1 : 1) * d;
      });
    }
    function cell(c, r) {
      const v = get(r, c.key);
      const td = U.el("td", { class: (c.num ? "num " : "") + (c.cls || "") });
      if (c.render) {
        const out = c.render(v, r);
        if (out instanceof Node) td.appendChild(out);
        else td.textContent = out;
      } else if (typeof v === "boolean") {
        td.appendChild(U.el("span", { class: v ? "yes" : "no", text: v ? "✓ yes" : "– no" }));
      } else td.textContent = c.fmt ? c.fmt(v, r) : U.fmt(c.key, v);
      return td;
    }
    function render() {
      header();
      tbody.textContent = "";
      const pages = Math.max(1, Math.ceil(refs.length / pageSize));
      page = Math.min(page, pages - 1);
      const start = page * pageSize;
      for (const r of refs.slice(start, start + pageSize)) {
        const tr = U.el("tr", { class: (opts.onRowClick ? "clickable " : "") + (opts.rowClass ? opts.rowClass(r) : "") });
        if (r === activeRef) tr.classList.add("active");
        if (opts.id) tr.appendChild(U.el("td", null, [U.starButton(opts.id(r), () => opts.record(r), opts.source)]));
        for (const c of opts.columns) tr.appendChild(cell(c, r));
        if (opts.onRowClick) tr.addEventListener("click", () => opts.onRowClick(r));
        tbody.appendChild(tr);
      }
      pager.textContent = "";
      if (refs.length > pageSize) {
        const prev = U.el("button", { type: "button", text: "‹ Prev", disabled: page === 0 ? true : null, onclick: () => { page--; render(); } });
        const next = U.el("button", { type: "button", text: "Next ›", disabled: page >= pages - 1 ? true : null, onclick: () => { page++; render(); } });
        pager.append(prev, U.el("span", { class: "muted", text: "Page " + (page + 1) + " of " + pages.toLocaleString() }), next);
      }
      pager.appendChild(
        U.el("span", { class: "muted", text: refs.length.toLocaleString() + " row" + (refs.length === 1 ? "" : "s") + (opts.note ? " · " + opts.note() : "") })
      );
    }
    const api = {
      update() {
        refs = opts.rows().slice();
        sortRefs();
        render();
      },
      redraw: render,
      setColumns(cols) {
        opts.columns = cols;
        if (sortKey && !cols.some((c) => c.key === sortKey)) sortKey = null;
      },
      setActive(ref) {
        activeRef = ref;
        const idx = refs.indexOf(ref);
        if (idx >= 0) page = Math.floor(idx / pageSize);
        render();
      },
    };
    Sel.onChange(() => tbody.querySelectorAll(".star").forEach((b) => b._sync && b._sync()));
    api.update();
    return api;
  };

  // Columns for a list of record objects, in data order, skipping some keys.
  U.columnsFor = function (keys, skip) {
    return keys
      .filter((k) => !(skip || []).includes(k))
      .map((k) => ({ key: k, label: U.label(k), num: !/variant|type|case|reason|id|architecture|source|saved|status|chassis|frame|battery|attribute|ranking|kind|charger|motor|autonomy/.test(k) || /^n_/.test(k) }));
  };

  // ---------- small SVG legend keys ----------
  U.shapeSvg = function (shape, color, size) {
    const s = size || 12;
    const ns = "http://www.w3.org/2000/svg";
    const svg = document.createElementNS(ns, "svg");
    svg.setAttribute("width", s);
    svg.setAttribute("height", s);
    svg.setAttribute("viewBox", "-6 -6 12 12");
    svg.setAttribute("class", "key");
    svg.setAttribute("aria-hidden", "true");
    let node;
    if (shape === "circle") {
      node = document.createElementNS(ns, "circle");
      node.setAttribute("r", "4.5");
    } else if (shape === "square") {
      node = document.createElementNS(ns, "rect");
      node.setAttribute("x", "-4");
      node.setAttribute("y", "-4");
      node.setAttribute("width", "8");
      node.setAttribute("height", "8");
    } else if (shape === "triangle") {
      node = document.createElementNS(ns, "path");
      node.setAttribute("d", "M0,-5 L5,4.5 L-5,4.5 Z");
    } else if (shape === "line") {
      node = document.createElementNS(ns, "line");
      node.setAttribute("x1", "-6");
      node.setAttribute("x2", "6");
      node.setAttribute("stroke", color);
      node.setAttribute("stroke-width", "2");
    } else if (shape === "ring") {
      node = document.createElementNS(ns, "circle");
      node.setAttribute("r", "4.5");
      node.setAttribute("fill", "none");
      node.setAttribute("stroke", color);
      node.setAttribute("stroke-width", "1.6");
    } else if (shape === "star") {
      node = document.createElementNS(ns, "path");
      node.setAttribute("d", starPath(0, 0, 6, 2.6));
    }
    if (shape !== "line" && shape !== "ring") node.setAttribute("fill", color);
    svg.appendChild(node);
    return svg;
  };
  function starPath(cx, cy, R, r) {
    let d = "";
    for (let i = 0; i < 10; i++) {
      const rad = i % 2 ? r : R;
      const a = -Math.PI / 2 + (i * Math.PI) / 5;
      d += (i ? "L" : "M") + (cx + rad * Math.cos(a)).toFixed(2) + "," + (cy + rad * Math.sin(a)).toFixed(2);
    }
    return d + "Z";
  }
  U.legendItem = (keyNode, text) => U.el("span", { class: "item" }, [keyNode, U.el("span", { text })]);

  // Redraw hooks for theme changes.
  U.onTheme = function (fn) {
    try {
      window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", fn);
    } catch (e) {
      /* old browsers */
    }
  };
})();
