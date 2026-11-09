import io
import json
import threading
import time
import urllib.request
import zipfile
from dataclasses import fields

import numpy as np
import pytest

from os4.lab.config import from_scenario, to_scenario, validate
from os4.lab.presets import presets
from os4.lab.run import calculate
from os4.lab.server import serve
from os4.scenario import primary_scenario
from os4.tradespace import tradespace
from os4.utility import load_weights
from os4.vehicle import bike_variants, road_variants

SMALL = {"road": [[1, 4, 1], [10, 30, 10]], "bike": [[5, 50, 15], [100, 250, 75]]}


def _small(cfg):
    return {**cfg, "grid": SMALL}


def test_config_round_trip_reproduces_the_primary_scenario():
    base = primary_scenario()
    back = to_scenario(json.loads(json.dumps(from_scenario(base, battery_case="removable"), allow_nan=False)))
    for f in fields(base):
        if f.name in ("demand", "notes"):
            continue
        assert getattr(back, f.name) == getattr(base, f.name), f.name
    assert np.allclose(back.demand.to_numpy(float), base.demand.to_numpy(float))


def test_fixed_battery_case_keeps_only_fixed_bikes():
    cfg = from_scenario(primary_scenario(), battery_case="fixed")
    assert to_scenario(cfg).bike_spare_options == (0.0,)
    assert to_scenario({**cfg, "battery_case": "removable"}).bike_spare_options == primary_scenario().bike_spare_options


@pytest.mark.parametrize("bad", [{"battery_case": "solar"}, {"weights": {"wait_time": 0.5}},
                                 {"grid": {"road": [[5, 1, 1]], "bike": [[5, 50, 5]]}},
                                 {"scenario": {"demand": [[0, 10], [2, 10], [3, 10]]}}])
def test_validate_rejects_bad_configs(bad):
    with pytest.raises(ValueError):
        validate({**from_scenario(primary_scenario()), **bad})


def test_every_preset_builds_and_scores():
    ps = presets()
    by_id = {p["id"]: p for p in ps}
    assert ps[0]["id"] == "standard" and {"report", "red_line", "network", "winter", "rush"} <= set(by_id)
    # The lab defaults to the posted limit and the Appendix B e-bike formula; "report" is the Task 3 run.
    standard = by_id["standard"]["config"]["scenario"]
    assert standard["road_speed_basis"] == "posted" and standard["bike_speed_basis"] == "formula"
    assert by_id["report"]["config"] == from_scenario(primary_scenario(), "Task 3 report settings")
    for p in ps:
        result = calculate(_small(p["config"]))
        assert result["summary"]["feasible"] > 0, p["id"]
        json.dumps(result, allow_nan=False)


def test_custom_weights_match_the_reweight_column():
    s = primary_scenario()
    grid = dict(n_road=(0, 2, 5), n_bike=(0, 20, 125))
    default = tradespace(s, **grid)
    reweighted = tradespace(s, weights=load_weights("os3a_reweight"), **grid)
    assert np.allclose(reweighted["mau"], default["mau_os3a_reweight"])
    assert np.allclose(tradespace(s, weights=load_weights(), **grid)["mau"], default["mau"])


def test_range_factor_scales_range_and_lowers_availability():
    from dataclasses import replace
    base, cold = primary_scenario(), replace(primary_scenario(), range_factor=0.75)
    for fn in (road_variants, bike_variants):
        a, b = fn(base), fn(cold)
        assert np.allclose(b["range_km"], 0.75 * a["range_km"])
        assert (b["availability"] <= a["availability"] + 1e-12).all()


def test_baseline_run_matches_task3():
    s = calculate(next(p for p in presets() if p["id"] == "report")["config"])["summary"]
    assert s["cheapest"]["cost"] == 182_200
    assert s["knee"]["cost"] == 275_950
    assert s["max_mau"] == pytest.approx(0.962, abs=5e-4)


def test_calculate_uses_the_disk_cache(tmp_path):
    cfg = _small(presets()[0]["config"])
    first = calculate(cfg, cache_dir=tmp_path)
    second = calculate(cfg, cache_dir=tmp_path)
    assert not first["cached"] and second["cached"] and second["summary"] == first["summary"]


def test_server_runs_a_job(tmp_path):
    server = serve(port=0, cache_dir=tmp_path)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        presets_ = json.load(urllib.request.urlopen(url + "/api/presets"))
        assert urllib.request.urlopen(url + "/").status == 200
        assert urllib.request.urlopen(url + "/assets/common.js").status == 200
        body = json.dumps(_small(presets_[0]["config"])).encode()
        req = urllib.request.Request(url + "/api/jobs", data=body, headers={"Content-Type": "application/json"})
        job_id = json.load(urllib.request.urlopen(req))["job_id"]
        for _ in range(200):
            job = json.load(urllib.request.urlopen(f"{url}/api/jobs/{job_id}"))
            if job["status"] in ("done", "error"):
                break
            time.sleep(0.05)
        assert job["status"] == "done" and job["result"]["summary"]["feasible"] > 0
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(url + "/static/../server.py")
    finally:
        server.shutdown()
        server.server_close()


def test_speed_choice_sets_the_road_cap_and_bike_speed():
    cfg = from_scenario(primary_scenario())
    s = cfg["scenario"]
    assert s["road_speed_basis"] == "achieved" and s["bike_speed_basis"] == "formula"
    posted = {**cfg, "scenario": {**s, "road_speed_basis": "posted"}}
    assert to_scenario(posted).speed_limit_kmh == pytest.approx(20 * 1.609344)
    formula = {**cfg, "scenario": {**s, "bike_speed_basis": "formula"}}
    assert to_scenario(formula).bike_assisted_speed_kmh is None
    assisted = {**cfg, "scenario": {**s, "bike_speed_basis": "assisted"}}
    assert to_scenario(assisted).bike_assisted_speed_kmh == 18.0
    # A config saved before the choice existed (only speed_limit_kmh) still loads, as an achieved cap.
    legacy = {**cfg, "scenario": {"speed_limit_kmh": 25.0, "bike_assisted_speed_kmh": None}}
    assert to_scenario(legacy).speed_limit_kmh == 25.0 and to_scenario(legacy).bike_assisted_speed_kmh is None


def test_tags_are_scored_and_checked_against_the_front():
    from os4.lab.run import evaluate_tags
    cfg = next(p for p in presets() if p["id"] == "report")["config"]
    result = calculate(cfg)
    knee = result["summary"]["knee"]["fleet"].replace(" × ", "×")
    tags = evaluate_tags(cfg, [{"id": knee, "label": "knee"}, {"id": "6 x C4-P2-G3-M2-A3", "label": "ref"},
                               {"id": "nonsense"}], result["front"])
    assert tags[0]["status"] == "ok" and not tags[0]["dominated"] and tags[0]["fleet_cost_usd"] == 275_950
    assert tags[1]["dominated"] and tags[1]["fleet_cost_usd"] == 430_800
    assert "cannot read" in tags[2]["status"]
    red_line = next(p for p in presets() if p["id"] == "red_line")["config"]
    assert "not available" in evaluate_tags(red_line, [{"id": "6×C4-P2-G3-M2-A3"}], [])[0]["status"]


def test_limit_grid_trims_the_tail_to_the_limit():
    from os4.lab.run import DEFAULT_LIMIT, estimate, limit_grid
    cfg = next(p for p in presets() if p["id"] == "standard")["config"]
    assert estimate(cfg)["architectures"] > DEFAULT_LIMIT
    trimmed, note = limit_grid(cfg)
    assert note["to"] <= DEFAULT_LIMIT and estimate(trimmed)["architectures"] == note["to"]
    assert trimmed["grid"]["road"][0] == cfg["grid"]["road"][0]  # the small fleets stay
    small = {**cfg, "grid": SMALL}
    assert limit_grid(small)[1] is None


def test_validate_caps_the_grid():
    cfg = from_scenario(primary_scenario())
    with pytest.raises(ValueError):
        validate({**cfg, "grid": {"road": [[1, 1000, 1]], "bike": [[5, 50, 5]]}})


def _post(url, payload, cookie=None):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Content-Type": "application/json", **({"Cookie": cookie} if cookie else {})})
    return urllib.request.urlopen(req)


def test_server_password_queue_and_cache_cap(tmp_path):
    from os4.lab.server import Busy, Lab
    server = serve(port=0, cache_dir=tmp_path, password="secret")
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        assert json.load(urllib.request.urlopen(url + "/api/session")) == {"auth_required": True, "ok": False}
        with pytest.raises(urllib.error.HTTPError) as e:
            urllib.request.urlopen(url + "/api/presets")
        assert e.value.code == 401
        with pytest.raises(urllib.error.HTTPError) as e:
            _post(url + "/api/login", {"password": "nope"})
        assert e.value.code == 403
        res = _post(url + "/api/login", {"password": "secret"})
        cookie = res.headers["Set-Cookie"].split(";")[0]
        req = urllib.request.Request(url + "/api/presets", headers={"Cookie": cookie})
        assert urllib.request.urlopen(req).status == 200
        est = json.load(_post(url + "/api/estimate", {"config": presets()[0]["config"], "limit": True}, cookie))
        assert est["architectures"] <= 1_500_000 and est["limited"]
    finally:
        server.shutdown()
        server.server_close()
    # queue: a full queue refuses new runs
    lab = Lab(None, max_queue=0)
    with pytest.raises(Busy):
        lab.submit(_small(presets()[1]["config"]))
    # cache cap: least recently used files go first
    lab = Lab(tmp_path, cache_max_mb=0.001)
    for i in range(3):
        (tmp_path / f"r{i}.json").write_text("x" * 600)
        time.sleep(0.01)
    lab._trim_cache()
    assert [p.name for p in tmp_path.glob("*.json")] == ["r2.json"]


def test_server_renders_figures(tmp_path):
    server = serve(port=0, cache_dir=tmp_path)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{server.server_address[1]}"
    try:
        job_id = json.load(_post(url + "/api/figures", {"config": _small(presets()[0]["config"]), "limit": False}))["job_id"]
        for _ in range(1200):
            job = json.load(urllib.request.urlopen(f"{url}/api/jobs/{job_id}"))
            if job["status"] in ("done", "error"):
                break
            time.sleep(0.05)
        assert job["status"] == "done", job.get("error")
        key, files = job["result"]["key"], job["result"]["files"]
        assert {"tradespace.png", "knee.png"} <= set(files)
        png = urllib.request.urlopen(f"{url}/api/figures/{key}/knee.png")
        assert png.headers["Content-Type"] == "image/png" and png.read(8) == b"\x89PNG\r\n\x1a\n"
        with zipfile.ZipFile(io.BytesIO(urllib.request.urlopen(f"{url}/api/figures/{key}.zip").read())) as zf:
            assert {"config.json", "pareto_front.csv", *files} <= set(zf.namelist())
            assert json.loads(zf.read("config.json"))["kind"] == "os4-lab-config"
        assert (tmp_path / f"{key}.zip").exists()  # cached on disk too
        with pytest.raises(urllib.error.HTTPError):
            urllib.request.urlopen(f"{url}/api/figures/{key}/../server.py")
    finally:
        server.shutdown()
        server.server_close()
