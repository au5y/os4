"""Build the model ZIP for the Canvas submission: executables and instructions on top, source beside them.

    uv run --with weasyprint python scripts/build_submission.py   # -> dist/OS4_H2-13_model.zip

The executables and the Excel workbook come from a GitHub Release (default: the frozen baseline,
``v1.1-weekday-final``, PLAN.md Q28), downloaded with the ``gh`` CLI. The source is this checkout's
committed files (``git archive HEAD``), so commit first. Needs ``gh``, ``git`` and ``zip`` (the
``zip`` tool keeps the executables' run permission, which macOS and Linux need).

Layout of the ZIP (one folder, so it unzips tidily):

    OS4_H2-13_model/
        OS4_How_to_Run.pdf      instructions and AI disclosure (from docs/HOW_TO_RUN.md)
        os4-windows.exe         standalone executables: double-click to open the Model Lab
        os4-mac                 (Apple Silicon)
        os4-linux
        os4_model.xlsx          Excel backup with live formulas
        README.md, src/, data/, tests/, scripts/, docs/, pyproject.toml, uv.lock, LICENSE
"""

import argparse
import shutil
import subprocess
import tarfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
NAME = "OS4_H2-13_model"
# Committed paths that go in the ZIP. Left out: resources/ (the assignment PDFs and slides), .github/,
# CLAUDE.md (assistant instructions) and outputs/ (generated; the executables and source runs write it).
SOURCE = ["README.md", "LICENSE", "pyproject.toml", "uv.lock", "src", "data", "tests", "scripts",
          "docs/PLAN.md", "docs/references.md"]
EXECUTABLES = {  # release asset -> (member inside it, name in the ZIP)
    "os4-windows-x64.zip": ("os4.exe", "os4-windows.exe"),
    "os4-macos-arm64.tar.gz": ("os4", "os4-mac"),
    "os4-linux-x64.tar.gz": ("os4", "os4-linux"),
}


def run(*cmd: str, **kw) -> None:
    subprocess.run(cmd, check=True, **kw)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--tag", default="v1.1-weekday-final", help="release to take executables and workbook from")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / f"{NAME}.zip")
    args = parser.parse_args()

    work = ROOT / "build" / "submission"
    shutil.rmtree(work, ignore_errors=True)
    downloads, stage = work / "downloads", work / NAME
    downloads.mkdir(parents=True)
    stage.mkdir()

    run("gh", "release", "download", args.tag, "-D", str(downloads), "-p", "os4_model.xlsx",
        *(arg for asset in EXECUTABLES for arg in ("-p", asset)), cwd=ROOT)
    for asset, (member, name) in EXECUTABLES.items():
        path = downloads / asset
        if asset.endswith(".zip"):
            with zipfile.ZipFile(path) as z, z.open(member) as src, open(stage / name, "wb") as dst:
                shutil.copyfileobj(src, dst)
        else:
            with tarfile.open(path) as t, t.extractfile(member) as src, open(stage / name, "wb") as dst:
                shutil.copyfileobj(src, dst)
        (stage / name).chmod(0o755)
    shutil.copy(downloads / "os4_model.xlsx", stage)

    archive = work / "source.tar"
    run("git", "archive", "--format=tar", "-o", str(archive), "HEAD", *SOURCE, cwd=ROOT)
    with tarfile.open(archive) as t:
        t.extractall(stage, filter="data")
    archive.unlink()

    run("python", str(ROOT / "scripts" / "build_how_to_run_pdf.py"), "--out", str(stage / "OS4_How_to_Run.pdf"))

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.unlink(missing_ok=True)
    run("zip", "-qrX", str(args.out.resolve()), NAME, cwd=work)
    print(f"{args.out} ({args.out.stat().st_size / 1e6:.0f} MB)")


if __name__ == "__main__":
    main()
