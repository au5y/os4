from os4.data import load, load_all


def test_all_tables_load():
    tables = load_all()
    assert len(tables) == 16
    assert all(len(df) > 0 for df in tables.values())


def test_mau_weights_sum_to_one():
    assert abs(load("mau_weights")["weight"].sum() - 1.0) < 1e-9
