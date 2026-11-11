(function () {
  "use strict";
  const U = OS4.util;
  const el = U.el;
  U.header("index.html");
  const m = OS4.meta || { cases: {}, grid: {} };

  const g = m.grid || {};
  const gridText = ["n_road", "n_bike"]
    .filter((k) => g[k])
    .map((k) => (k === "n_road" ? "road " : "bikes ") + g[k].min + "–" + g[k].max + " (" + g[k].count + " sizes)")
    .join(", ");
  document.getElementById("summary").appendChild(
    el("p", null, ["Scenario: ", el("b", { text: m.scenario || "?" }), ". Fleet-size grid: " + (gridText || "?") + "."])
  );

  const cases = Object.entries(m.cases || {});
  const tasks = [
    ["task1.html", "Task 1 · Stakeholder utility", "SAU curves, cases A–C, MAU under each weight set, weight sensitivity.", "done", null],
    ["task2.html", "Task 2 · Technical system model", "The five Task 2 architectures, ~50 highlighted candidates to pick from, and every vehicle variant.", "done", null],
    [
      "task3.html",
      "Task 3 · Tradespace",
      "Utility vs. cost for every feasible architecture, Pareto front, battery-case and utility toggles, filters.",
      "done",
      cases.map(([k, c]) => k + ": " + c.architectures.toLocaleString() + " architectures, " + c.front + " on the front").join(" · "),
    ],
    ["task4.html", "Task 4 · Second operating scenario", "The Red Line disruption against the standard weekday: both Pareto fronts, the Task 3 picks in each, and how we resolve the conflict.", "done", null],
    ["task5.html", "Task 5 · Recommended concept", "A fleet that scales for closures: 2 A4 buses + 20 e-bikes every weekday, plus a surge kit of 4 buses + 10 e-bikes for Red Line closures.", "done", null],
  ];
  const box = document.getElementById("tasks");
  for (const [href, title, text, status, stat] of tasks) {
    box.appendChild(
      el(href ? "a" : "div", { class: "card" + (href ? "" : " disabled"), href }, [
        el("h3", { text: title }),
        el("span", { class: "tag", text: status }),
        el("p", { class: "muted", text }),
        stat ? el("p", { class: "small", text: stat }) : null,
      ])
    );
  }
  U.footer();
})();
