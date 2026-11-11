"""Where the model finds its inputs and writes its outputs, from a checkout or from the standalone executable.

From a checkout (``uv run python -m os4``) everything is relative to the repository root: inputs in ``data/``,
team documents in ``docs/``, outputs in ``outputs/``.

The standalone executable (built by ``scripts/build_exe.py`` with PyInstaller) unpacks ``data/`` and ``docs/``
into its bundle folder (``sys._MEIPASS``: a temporary folder for the default one-file build, a folder beside
the executable for ``--onedir``) and writes ``outputs/`` next to the executable itself.
"""

import sys
from pathlib import Path

FROZEN = bool(getattr(sys, "frozen", False))
REPO_ROOT = Path(__file__).resolve().parents[2]
BUNDLE_ROOT = Path(getattr(sys, "_MEIPASS", REPO_ROOT)) if FROZEN else REPO_ROOT

DATA_DIR = BUNDLE_ROOT / "data"
DOCS_DIR = BUNDLE_ROOT / "docs"
OUTPUT_DIR = (Path(sys.executable).resolve().parent if FROZEN else REPO_ROOT) / "outputs"
