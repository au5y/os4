from openpyxl import load_workbook

from os4.export import export_task1


def test_task1_workbook_has_formulas_and_python_checks(tmp_path):
    path = export_task1(tmp_path / "model.xlsx")
    wb = load_workbook(path)
    assert wb.sheetnames == ["README", "SAU", "Weights", "Cases", "Sensitivity"]
    cases = wb["Cases"]
    assert [cases.cell(row=r, column=1).value for r in (4, 5, 6)] == ["A", "B", "C"]
    # SAU and MAU cells are live formulas; the python column holds the code's value.
    assert str(cases["F4"].value).startswith("=IF(")
    assert str(cases["J4"].value).startswith("=Weights!")
    assert cases["L4"].value == 0.613
    assert {"x_wait_time", "u_wait_time", "m_wait_time", "x_travel_time"} <= set(wb.defined_names)


def test_full_model_workbook_adds_task2_sheets(tmp_path):
    from os4.export import export_model
    from os4.scenario import primary_scenario
    from os4.vehicle import all_variants

    wb = load_workbook(export_model(primary_scenario(), tmp_path / "model.xlsx"))
    assert wb.sheetnames[-3:] == ["Scenario", "Variants", "Architectures"]
    variants = wb["Variants"]
    assert variants.max_row - 4 == len(all_variants(primary_scenario()))
    assert str(variants["Y5"].value).startswith("=")  # weight formula
    assert {"road_speed_cap", "demand_trips", "v_variant_id"} <= set(wb.defined_names)


def test_every_formula_function_opens_in_excel(tmp_path):
    # openpyxl writes formula text verbatim, so any function added in Excel 2010 or later (e.g. NORM.S.DIST)
    # must carry an _xlfn. prefix or Excel shows #NAME?. Every function used must be a classic one.
    import re

    from openpyxl.utils import FORMULAE

    from os4.export import export_model
    from os4.scenario import primary_scenario

    wb = load_workbook(export_model(primary_scenario(), tmp_path / "model.xlsx"))
    used = set()
    for ws in wb.worksheets:
        for row in ws.iter_rows():
            for cell in row:
                if isinstance(cell.value, str) and cell.value.startswith("="):
                    used |= set(re.findall(r"([A-Z][A-Z0-9.]*)\(", cell.value))
    unknown = {f for f in used if f not in FORMULAE and not f.startswith("_xlfn.")}
    assert not unknown, f"functions Excel may not recognise without an _xlfn. prefix: {sorted(unknown)}"
    assert "NORMSDIST" in used
