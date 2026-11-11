"""Render docs/HOW_TO_RUN.md to a PDF for the model ZIP submission.

    uv run --with weasyprint python scripts/build_how_to_run_pdf.py   # -> dist/OS4_How_to_Run.pdf

WeasyPrint is not a project dependency (it needs the Pango system library), hence ``--with``.
"""

import argparse
import re
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parents[1]

CSS = """
@page { size: Letter; margin: 0.75in 0.8in;
        @bottom-right { content: "OS4 model · H2 Team 13 · page " counter(page) " of " counter(pages);
                        font: 8pt "DejaVu Sans", sans-serif; color: #666; } }
body { font: 10pt/1.45 "DejaVu Sans", sans-serif; color: #1a1a1a; }
h1 { font-size: 20pt; margin: 0 0 6pt; color: #0b3d6e; }
h2 { font-size: 13pt; margin: 16pt 0 5pt; padding-bottom: 2pt; border-bottom: 1.5pt solid #0b3d6e;
     color: #0b3d6e; page-break-after: avoid; }
h3 { font-size: 11pt; margin: 11pt 0 3pt; page-break-after: avoid; }
p, li { margin: 3pt 0; }
code { font: 8.5pt "DejaVu Sans Mono", monospace; background: #f1f3f6; padding: 0 2pt; border-radius: 2pt; }
pre { background: #f1f3f6; border-left: 3pt solid #0b3d6e; padding: 6pt 8pt; page-break-inside: avoid;
      white-space: pre-wrap; }
pre code { background: none; padding: 0; }
table { border-collapse: collapse; width: 100%; margin: 5pt 0; font-size: 9pt; page-break-inside: avoid; }
th { background: #0b3d6e; color: white; text-align: left; }
th code { background: rgba(255,255,255,0.2); color: white; }
th, td { border: 0.5pt solid #c5ccd6; padding: 3pt 5pt; vertical-align: top; }
tr:nth-child(even) td { background: #f7f9fb; }
a { color: #0b5cad; text-decoration: none; }
"""


URL = re.compile(r"(?<![<`/])(?<!\]\()(https?://[^\s|)`,]+?)(?=[.:;]?(?:\s|$|\||\)))")


def _autolink(lines: list[str]) -> str:
    """Wrap bare URLs in ``<...>`` so they become links, outside code blocks and inline code."""
    out, fenced = [], False
    for line in lines:
        if line.startswith("```"):
            fenced = not fenced
        if not fenced:
            parts = line.split("`")
            parts[::2] = [URL.sub(r"<\1>", part) for part in parts[::2]]
            line = "`".join(parts)
        out.append(line)
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--src", type=Path, default=ROOT / "docs" / "HOW_TO_RUN.md")
    parser.add_argument("--out", type=Path, default=ROOT / "dist" / "OS4_How_to_Run.pdf")
    args = parser.parse_args()

    from weasyprint import HTML

    text = args.src.read_text(encoding="utf-8")
    # Two trailing spaces force the line breaks in the title block.
    lines = text.splitlines()
    body_start = next(i for i, line in enumerate(lines) if line.startswith("## "))
    lines[:body_start] = [line + "  " if line.startswith("**") else line for line in lines[:body_start]]
    html = markdown.markdown(_autolink(lines), extensions=["tables", "fenced_code"])
    page = f"<!doctype html><html><head><meta charset='utf-8'><style>{CSS}</style></head><body>{html}</body></html>"
    args.out.parent.mkdir(parents=True, exist_ok=True)
    HTML(string=page, base_url=str(ROOT)).write_pdf(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
