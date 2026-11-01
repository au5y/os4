/* Components page: the Appendix C / D tables that variant ids are built from. */
(function () {
  const OS4 = window.OS4;
  const U = OS4.util;
  U.header("components.html");
  const host = document.getElementById("tables");
  const comps = (OS4.meta && OS4.meta.components) || {};
  const groups = [["road", "Road vehicle (Appendix C)"], ["bike", "E-bike (Appendix D)"]];
  for (const [kind, title] of groups) {
    host.appendChild(U.el("h2", { text: title }));
    for (const t of comps[kind] || []) {
      const cols = Object.keys(t.rows[0] || {});
      const units = t.units || {};
      const table = U.el("table", { class: "components-table" });
      table.appendChild(U.el("caption", { text: t.prefix + "  ·  " + t.title }));
      const head = U.el("tr");
      for (const c of cols) head.appendChild(U.el("th", { scope: "col", class: c === "id" ? "" : "num", text: c === "id" ? "code" : c.replace(/_(usd|kg|kwh|kw|wh_per_km)$/, "") + (units[c] ? " (" + units[c] + ")" : "") }));
      table.appendChild(U.el("thead", null, [head]));
      const body = U.el("tbody");
      for (const r of t.rows) {
        const tr = U.el("tr");
        for (const c of cols) tr.appendChild(U.el("td", { class: c === "id" ? "" : "num", text: c === "cost_usd" ? "$" + Number(r[c]).toLocaleString() : String(r[c]) }));
        body.appendChild(tr);
      }
      table.appendChild(body);
      host.appendChild(U.el("div", { class: "table-wrap" }, [table]));
    }
  }
  U.footer();
})();
