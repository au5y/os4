(function () {
  "use strict";
  const U = OS4.util;
  const el = U.el;
  const Sel = OS4.selection;
  U.header("selected.html");

  const actions = document.getElementById("actions");
  const exportLink = U.exportLink("⤓ Export CSV");
  exportLink.classList.add("primary");
  const clear = el("button", { type: "button", text: "Clear all" });
  let armed = false;
  clear.addEventListener("click", () => {
    if (!Sel.count()) return;
    if (!armed) {
      armed = true;
      clear.textContent = "Click again to clear " + Sel.count();
      setTimeout(() => { armed = false; clear.textContent = "Clear all"; }, 4000);
      return;
    }
    armed = false;
    clear.textContent = "Clear all";
    Sel.clear();
  });
  actions.append(exportLink, clear);
  if (!Sel.persistent()) {
    document.getElementById("storage-note").appendChild(
      el("div", { class: "banner", text: "This browser blocks localStorage for local files, so the selection lasts only while this page is open." })
    );
  }

  const LEAD = ["id", "source", "case", "reason", "architecture", "fleet_type", "road_variant", "n_road", "bike_variant", "n_bike", "fleet_cost_usd", "mau", "mau_os3a_extended"];
  const list = document.getElementById("list");
  function render() {
    list.textContent = "";
    const items = Object.values(Sel.all());
    if (!items.length) {
      list.appendChild(el("p", { class: "muted" }, ["Nothing selected yet. Star architectures on the ", el("a", { href: "task2.html", text: "Task 2" }), " or ", el("a", { href: "task3.html", text: "Task 3" }), " pages."]));
      return;
    }
    const rows = items.map((it) => Object.assign({}, it.record, { id: it.id, source: it.source }));
    const keys = [];
    for (const r of rows) for (const k of Object.keys(r)) if (!keys.includes(k)) keys.push(k);
    const ordered = LEAD.filter((k) => keys.includes(k)).concat(keys.filter((k) => !LEAD.includes(k) && !["road_chassis", "bike_frame"].includes(k)));
    U.Table(list, {
      columns: U.columnsFor(ordered).map((c) => (c.key === "reason" ? Object.assign(c, { cls: "wrap-text" }) : c)),
      rows: () => rows,
      id: (r) => r.id,
      record: (r) => r,
      sort: { key: "fleet_cost_usd", dir: 1 },
      pageSize: 100,
    });
  }
  Sel.onChange(render);
  render();
  U.footer();
})();
