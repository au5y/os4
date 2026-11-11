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


def test_every_text_read_and_write_names_its_encoding():
    # Windows defaults to cp1252, which can't write the reports' "≤" or "×" (the Windows build failed on it).
    import ast
    missing = []
    for path in (ROOT / "src").rglob("*.py"):
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
            if (isinstance(node, ast.Call) and getattr(node.func, "attr", None) in ("write_text", "read_text")
                    and not any(k.arg == "encoding" for k in node.keywords)):
                missing.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert not missing


def test_executable_with_no_arguments_opens_the_lab(monkeypatch):
    import os4.__main__ as entry
    import os4.lab.__main__ as lab_entry
    calls = []
    monkeypatch.setattr(entry, "FROZEN", True)
    monkeypatch.setattr(lab_entry, "main", lambda argv: calls.append(argv))
    entry.main([])
    assert calls == [["--open"]]


def test_run_prefix_runs_the_batch_model(tmp_path):
    main(["run", "--only", "task1", "--out", str(tmp_path), "--no-progress"])
    assert (tmp_path / "task1_cases.md").exists()


def test_lab_open_falls_back_to_a_free_port(monkeypatch):
    import socket

    import os4.lab.__main__ as lab_entry
    opened, served = [], []
    monkeypatch.setattr(lab_entry.webbrowser, "open", opened.append)
    monkeypatch.setattr(lab_entry.threading, "Timer", lambda _t, f, args: type("T", (), {"start": lambda s: f(*args)})())

    def fake_serve_forever(self):
        served.append(self.server_address[1])
        raise KeyboardInterrupt
    monkeypatch.setattr(lab_entry.serve.__globals__["ThreadingHTTPServer"], "serve_forever", fake_serve_forever)
    with socket.socket() as busy:
        busy.bind(("127.0.0.1", 0))
        busy.listen()
        taken = busy.getsockname()[1]
        lab_entry.main(["--open", "--port", str(taken), "--no-cache"])
    assert served and served[0] != taken
    assert opened == [f"http://127.0.0.1:{served[0]}"]
