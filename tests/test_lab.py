import json
import threading
import time
import urllib.request
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
    assert ps[0]["id"] == "standard" and ps[0]["config"] == from_scenario(primary_scenario(), ps[0]["name"])
    assert {"red_line", "network", "winter", "rush"} <= {p["id"] for p in ps}
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
    s = calculate(presets()[0]["config"])["summary"]
    assert s["cheapest"]["cost"] == 182_200
    assert s["knee"]["cost"] == 259_200
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
    assert s["road_speed_basis"] == "achieved" and s["bike_speed_basis"] == "assisted"
    posted = {**cfg, "scenario": {**s, "road_speed_basis": "posted"}}
    assert to_scenario(posted).speed_limit_kmh == pytest.approx(20 * 1.609344)
    formula = {**cfg, "scenario": {**s, "bike_speed_basis": "formula"}}
    assert to_scenario(formula).bike_assisted_speed_kmh is None
    # A config saved before the choice existed (only speed_limit_kmh) still loads, as an achieved cap.
    legacy = {**cfg, "scenario": {"speed_limit_kmh": 25.0, "bike_assisted_speed_kmh": None}}
    assert to_scenario(legacy).speed_limit_kmh == 25.0 and to_scenario(legacy).bike_assisted_speed_kmh is None
