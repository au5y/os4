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
