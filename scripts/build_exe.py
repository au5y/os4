"""Build the standalone ``os4`` executable with PyInstaller.

    uv sync --extra dev --extra build
    uv run python scripts/build_exe.py            # -> dist/os4 (dist/os4.exe on Windows)

The executable bundles Python, the dependencies, the ``os4`` package (with the explorer template and the
Model Lab page), ``data/`` and ``docs/``, so it runs on a machine with nothing installed. It is built for the
operating system it is built on: build on Windows for Windows, on macOS for macOS (CI builds all three).

    ./dist/os4                       # run Tasks 1-3; outputs/ is written next to the executable
    ./dist/os4 --only task1 --out X  # same options as python -m os4
    ./dist/os4 lab                   # the Model Lab on http://127.0.0.1:8411

Pass ``--onedir`` for a folder instead of a single file (starts faster; the single file unpacks itself to a
temporary folder on every run). Other arguments are passed to PyInstaller.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ENTRY = ROOT / "scripts" / "os4_entry.py"


def main(argv: list[str]) -> None:
    import PyInstaller.__main__

    onedir = "--onedir" in argv
    extra = [a for a in argv if a != "--onedir"]
    sep = os.pathsep  # PyInstaller's --add-data separator
    PyInstaller.__main__.run([
        str(ENTRY),
        "--name", "os4",
        "--onedir" if onedir else "--onefile",
        "--console",
        "--noconfirm",
        "--clean",
        "--paths", str(ROOT / "src"),
        "--distpath", str(ROOT / "dist"),
        "--workpath", str(ROOT / "build"),
        "--specpath", str(ROOT / "build"),
        "--collect-submodules", "os4",
        "--collect-data", "os4",  # site_template/ and lab/static/
        "--add-data", f"{ROOT / 'data'}{sep}data",
        "--add-data", f"{ROOT / 'docs'}{sep}docs",
        # Not used by the model; keeps the bundle smaller.
        "--exclude-module", "tkinter",
        "--exclude-module", "pytest",
        *extra,
    ])
    exe = ROOT / "dist" / ("os4" if onedir else "") / ("os4.exe" if sys.platform == "win32" else "os4")
    print(f"\nBuilt {exe}")


if __name__ == "__main__":
    main(sys.argv[1:])
