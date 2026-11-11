import json
import re

import pytest

from os4.scenario import primary_scenario
from os4.site import (arch_id, case_frames, highlight_architectures, link_questions, plan_questions, sample_rows,
                      write_docs, write_reports, write_site)
from os4.tradespace import pareto_front

GRID = {"n_road": (0, 5, 10, 20), "n_bike": (0, 25, 50, 100)}
CAP = 300
ASSIGN = re.compile(r'^window\.OS4 = window\.OS4 \|\| \{\};\nwindow\.OS4\["(\w+)"\] = (.*);\n$', re.S)


@pytest.fixture(scope="module")
def site(tmp_path_factory):
    out = tmp_path_factory.mktemp("site")
    paths = write_site(primary_scenario(), out, mixed_cap=CAP, reports_dir=None, docs_dir=None, **GRID)
    return out, paths


@pytest.fixture(scope="module")
def frames():
    return case_frames(primary_scenario(), **GRID)


def _data(out, name):
    match = ASSIGN.match((out / "data" / f"{name}.js").read_text(encoding="utf-8"))
    assert match, name
    assert match.group(1) == name
    return json.loads(match.group(2))


def test_writes_index_and_one_page_per_task(site):
    out, paths = site
    for page in ("index.html", "task1.html", "task2.html", "task3.html", "selected.html"):
        assert (out / page).exists(), page
        assert out / page in paths
    for html in out.glob("*.html"):
        text = html.read_text(encoding="utf-8")
        # Static site: everything is local, nothing fetched.
        assert "http://" not in text and "https://" not in text
    for js in (out / "assets").glob("*.js"):
        text = js.read_text(encoding="utf-8")
        assert "fetch(" not in text and "XMLHttpRequest" not in text


def test_every_data_js_assigns_valid_json(site):
    out, _ = site
    names = sorted(p.stem for p in (out / "data").glob("*.js"))
    assert names == ["meta", "task1", "task2", "task3_fixed", "task3_removable"]
    for name in names:
        assert isinstance(_data(out, name), dict)


def test_task3_sample_is_capped_and_keeps_the_front(site, frames):
    out, _ = site
    for key, df in frames.items():
        payload = _data(out, f"task3_{key}")
        table = payload["table"]
        assert payload["shown"]["mixed"] <= CAP
        assert payload["totals"]["all"] == len(df)
        assert payload["shown"]["road-only"] == payload["totals"]["road-only"]
        assert payload["shown"]["bike-only"] == payload["totals"]["bike-only"]
        assert len(table["data"]["fleet_cost_usd"]) == table["n"] == payload["shown"]["all"]
        # Every column of the tradespace is shipped.
        assert set(df.columns) <= {c["name"] for c in table["columns"]}
        dicts, data = table["dicts"], table["data"]

        def shipped_id(i):
            return arch_id({"road_variant": dicts["road_variant"][data["road_variant"][i]] if data["n_road"][i] else None,
                            "n_road": data["n_road"][i],
                            "bike_variant": dicts["bike_variant"][data["bike_variant"][i]] if data["n_bike"][i] else None,
                            "n_bike": data["n_bike"][i]})

        shipped = {shipped_id(i) for i in range(table["n"])}
        for utility in payload["utilities"]:
            front = pareto_front(df, utility)
            assert {arch_id(r) for _, r in front.iterrows()} <= shipped
            assert len(payload["fronts"][utility]) == len(front)
            costs = [data["fleet_cost_usd"][i] for i in payload["fronts"][utility]]
            assert costs == sorted(costs)


def test_sample_rows_respects_cap(frames):
    df = frames["removable"]
    idx = sample_rows(df, mixed_cap=50)
    assert idx.is_unique
    assert set(pareto_front(df).index) <= set(idx)
    front_mixed = sum((pareto_front(df, u)["fleet_type"] == "mixed").sum() for u in ("mau", "mau_appendix_a"))
    assert df.loc[idx, "fleet_type"].eq("mixed").sum() <= max(50, front_mixed)
    assert (df.loc[idx, "fleet_type"] != "mixed").sum() == (df["fleet_type"] != "mixed").sum()
    assert sample_rows(df, mixed_cap=50).equals(idx)  # seeded


def test_highlights_unique_with_reasons(frames, site):
    out, _ = site
    hl = highlight_architectures(frames)
    assert 10 <= len(hl) <= 60
    assert hl["id"].is_unique
    assert hl["reason"].str.len().gt(0).all()
    assert hl["case"].str.len().gt(0).all()
    # One cheapest road-only pick per chassis present in the data.
    road = frames["fixed"].query("fleet_type == 'road-only'")
    for chassis in road["road_chassis"].dropna().unique():
        assert hl["reason"].str.contains(f"cheapest road-only {chassis} ").any()
    shipped = _data(out, "task2")["highlights"]
    assert len({r["id"] for r in shipped}) == len(shipped)
    assert all(r["reason"] for r in shipped)


def test_task1_and_task2_payloads(site):
    out, _ = site
    t1 = _data(out, "task1")
    # Only weighted attributes get a curve on the page; travel time and bike share are unweighted.
    assert {s["attribute"] for s in t1["saus"]} == {"passenger_volume", "peak_throughput", "wait_time",
                                                    "availability"}
    assert [c["mau"] for c in t1["cases"]] == pytest.approx([0.613, 0.6385, 0.651], abs=1e-3)
    t2 = _data(out, "task2")
    assert len(t2["architectures"]) == 5
    assert t2["variants"]["n"] > 100


def test_components_reference(site):
    # The Appendix C / D tables behind every variant id ship with meta.js and get their own page.
    out, _ = site
    assert (out / "components.html").exists() and (out / "assets" / "components.js").exists()
    comps = _data(out, "meta")["components"]
    road = {t["prefix"]: t for t in comps["road"]}
    bike = {t["prefix"]: t for t in comps["bike"]}
    assert list(road) == ["C", "P", "G", "M", "A"] and list(bike) == ["B", "E", "G", "K"]
    assert len(road["C"]["rows"]) == 8 and road["C"]["rows"][4]["id"] == "C5"
    assert {r["id"] for r in road["A"]["rows"]} == {"A3", "A4", "A5"}


def test_reports_are_rendered_with_their_images(tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "task9_demo.md").write_text(
        "# Demo report\n\n| a | b |\n| --- | --- |\n| 1 | 2 |\n\n![Chart](media/chart.png)\n", encoding="utf-8")
    (src / "media").mkdir()
    (src / "media" / "chart.png").write_bytes(b"png")
    out = tmp_path / "site"
    out.mkdir()
    paths = write_reports(src, out)
    page = (out / "report_task9_demo.html").read_text(encoding="utf-8")
    assert "<title>OS4 · Demo report</title>" in page
    assert '<div class="table-wrap"><table>' in page
    assert 'src="img/chart.png"' in page and (out / "img" / "chart.png").exists()
    assert 'href="report_task9_demo.html"' in (out / "reports.html").read_text(encoding="utf-8")
    assert out / "reports.html" in paths


def test_report_is_embedded_in_its_page_slot(tmp_path):
    src, out = tmp_path / "src", tmp_path / "site"
    src.mkdir(), out.mkdir()
    (src / "task9_demo.md").write_text("# Demo report\n\n## Results\n\nBody text.\n", encoding="utf-8")
    slot = "<h2>Write-up</h2>\n<!-- report:task9_demo -->\n<p>fallback</p>\n<!-- /report -->\n"
    (out / "task9.html").write_text(slot, encoding="utf-8")
    (out / "other.html").write_text("<!-- report:task8_other -->\n<p>fallback</p>\n<!-- /report -->", encoding="utf-8")
    write_reports(src, out)
    page = (out / "task9.html").read_text(encoding="utf-8")
    assert '<h3 id="results">Results</h3>' in page and "Body text." in page
    assert "fallback" not in page and "Demo report" not in page
    assert "fallback" in (out / "other.html").read_text(encoding="utf-8")


def test_long_report_tables_start_collapsed(tmp_path):
    src, out = tmp_path / "src", tmp_path / "site"
    src.mkdir(), out.mkdir()
    rows = "".join(f"| {i} | x |\n" for i in range(20))
    (src / "task9_demo.md").write_text(f"# Demo\n\n| a | b |\n| --- | --- |\n{rows}\n| a | b |\n| --- | --- |\n| 1 | 2 |\n",
                                      encoding="utf-8")
    write_reports(src, out)
    page = (out / "report_task9_demo.html").read_text(encoding="utf-8")
    assert page.count('<details class="long-table">') == 1
    assert "Table: 20 rows (click to expand)" in page


def test_plan_is_rendered_view_only_with_working_links(tmp_path):
    docs, out = tmp_path / "docs", tmp_path / "site"
    docs.mkdir(), out.mkdir()
    (docs / "PLAN.md").write_text("# Plan\n\nSee [[1]](references.md#ref-1) and [cases](../outputs/task1_cases.md).\n\n"
                                  "$$U = \\sum k_i u_i$$\n", encoding="utf-8")
    (docs / "references.md").write_text("# References\n\n1. <a id=\"ref-1\"></a>Source.\n", encoding="utf-8")
    write_docs(docs, out)
    page = (out / "plan.html").read_text(encoding="utf-8")
    assert "View only." in page and 'OS4.util.header("plan.html")' in page
    assert 'href="references.html#ref-1"' in page and 'href="report_task1_cases.html"' in page
    assert '<div class="math">\\[U = \\sum k_i u_i\\]</div>' in page and "katex.min.js" in page
    assert (out / "references.html").exists()


def test_question_ids_link_to_their_definition_in_the_plan(tmp_path):
    docs, out = tmp_path / "docs", tmp_path / "site"
    docs.mkdir(), out.mkdir()
    (docs / "PLAN.md").write_text("# Plan\n\n#### <a id=\"q3\"></a>Q3. How fast is `it`?\n\n**Answer:** 21.\n\n"
                                  "See [Q3](#q3), Q3, Q9 and `Q3`.\n", encoding="utf-8")
    write_docs(docs, out)
    (out / "task2.html").write_text("<p>See PLAN.md Q3.</p>", encoding="utf-8")
    questions = plan_questions(docs / "PLAN.md")
    assert questions == {"3": "How fast is it?"}
    link_questions(out, questions)
    plan = (out / "plan.html").read_text(encoding="utf-8")
    tip = 'title="Q3. How fast is it?"'
    assert plan.count('id="q3"') == 1
    assert f'See <a class="qref" href="#q3" {tip}>Q3</a>, <a class="qref" href="#q3" {tip}>Q3</a>, Q9 and <code>Q3</code>' in plan
    assert f'<a class="qref" href="plan.html#q3" {tip}>Q3</a>' in (out / "task2.html").read_text(encoding="utf-8")
