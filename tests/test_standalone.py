"""Paths and entry point used by the standalone executable (scripts/build_exe.py)."""

import importlib
import sys
from pathlib import Path

import pytest

import os4.paths
from os4.__main__ import main

ROOT = Path(__file__).resolve().parents[1]


def test_paths_from_a_checkout_point_at_the_repo():
    assert not os4.paths.FROZEN
    assert os4.paths.DATA_DIR == ROOT / "data"
    assert os4.paths.DOCS_DIR == ROOT / "docs"
    assert os4.paths.OUTPUT_DIR == ROOT / "outputs"


def test_frozen_paths_use_the_bundle_and_the_executable_folder(monkeypatch, tmp_path):
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "_MEIPASS", str(tmp_path / "bundle"), raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "app" / "os4"))
    try:
        paths = importlib.reload(os4.paths)
        assert paths.FROZEN
        assert paths.DATA_DIR == tmp_path / "bundle" / "data"
        assert paths.DOCS_DIR == tmp_path / "bundle" / "docs"
        assert paths.OUTPUT_DIR == tmp_path / "app" / "outputs"
    finally:
        monkeypatch.undo()
        importlib.reload(os4.paths)


def test_lab_subcommand_dispatches_to_the_model_lab(capsys):
    with pytest.raises(SystemExit) as exit_:
        main(["lab", "--help"])
    assert exit_.value.code == 0
    assert "Model Lab" in capsys.readouterr().out


def test_task1_runs_into_another_folder(tmp_path):
    main(["--only", "task1", "--out", str(tmp_path), "--no-progress"])
    assert (tmp_path / "task1_cases.md").exists()
    assert (tmp_path / "media" / "task1_sau_curves.png").exists()
