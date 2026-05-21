"""Render the trainer-facing markdown docs to PDF.

Pipeline: markdown -> HTML (via the `markdown` package, with the
extensions we need) -> PDF (via Microsoft Edge in headless mode using
its built-in --print-to-pdf flag).

Output: manuals/TRAINER_GUIDE.pdf, manuals/REFERENCE_CARD.pdf
"""

import os
import shutil
import subprocess
import sys
import tempfile

import markdown

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS_DIR = os.path.join(REPO_ROOT, "docs")
OUT_DIR = os.path.join(REPO_ROOT, "manuals")

EDGE_CANDIDATES = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
]

# Print-friendly CSS. Page margins generous enough that the reference
# card stays one page; tables use a clean grid; ASCII boxes (in <pre>
# blocks) use a monospace font wide enough that the characters align.
CSS = """
@page {
  size: Letter;
  margin: 0.75in 0.7in;
}
body {
  font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
  font-size: 11pt;
  line-height: 1.45;
  color: #111;
  max-width: none;
}
h1 {
  font-size: 22pt;
  border-bottom: 2px solid #333;
  padding-bottom: 4pt;
  margin-top: 0;
}
h2 {
  font-size: 15pt;
  margin-top: 18pt;
  border-bottom: 1px solid #bbb;
  padding-bottom: 2pt;
  page-break-after: avoid;
}
h3 {
  font-size: 12pt;
  margin-top: 12pt;
  page-break-after: avoid;
}
p, ul, ol, table {
  margin-top: 6pt;
  margin-bottom: 6pt;
}
ul, ol {
  padding-left: 22pt;
}
li {
  margin-bottom: 2pt;
}
table {
  border-collapse: collapse;
  width: 100%;
}
th, td {
  border: 1px solid #999;
  padding: 5pt 8pt;
  vertical-align: top;
  text-align: left;
}
th {
  background: #eee;
}
code {
  font-family: Consolas, "Courier New", monospace;
  font-size: 10pt;
  background: #f4f4f4;
  padding: 1pt 3pt;
  border-radius: 2pt;
}
pre {
  font-family: Consolas, "Courier New", monospace;
  font-size: 9pt;
  background: #f7f7f7;
  border: 1px solid #ddd;
  border-radius: 3pt;
  padding: 8pt 10pt;
  white-space: pre;
  overflow-x: auto;
  line-height: 1.25;
  page-break-inside: avoid;
}
pre code {
  background: transparent;
  padding: 0;
  font-size: inherit;
}
blockquote {
  margin: 8pt 0;
  padding: 6pt 12pt;
  border-left: 3pt solid #888;
  background: #f7f7f7;
  color: #333;
}
hr {
  border: none;
  border-top: 1px solid #bbb;
  margin: 14pt 0;
}
a { color: #1a3d7c; text-decoration: none; }
"""

HTML_TEMPLATE = """<!doctype html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>{css}</style>
</head><body>
{body}
</body></html>
"""


def find_edge():
    for p in EDGE_CANDIDATES:
        if os.path.exists(p):
            return p
    raise SystemExit("Microsoft Edge not found in the expected locations.")


def md_to_html(md_path, title):
    with open(md_path, "r", encoding="utf-8") as f:
        body = markdown.markdown(
            f.read(),
            extensions=["tables", "fenced_code", "sane_lists"],
        )
    return HTML_TEMPLATE.format(title=title, css=CSS, body=body)


def html_to_pdf(edge, html_path, pdf_path):
    # Edge needs file:// URLs. --headless=new is the modern flag for
    # Chromium 109+ (Edge 109+); --print-to-pdf renders the loaded page.
    url = "file:///" + html_path.replace("\\", "/")
    cmd = [
        edge,
        "--headless=new",
        "--disable-gpu",
        "--no-pdf-header-footer",
        f"--print-to-pdf={pdf_path}",
        url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
    if result.returncode != 0:
        print("Edge stderr:", result.stderr, file=sys.stderr)
        raise SystemExit(f"Edge returned {result.returncode}")


def build(md_filename, title):
    md_path = os.path.join(DOCS_DIR, md_filename)
    if not os.path.exists(md_path):
        raise SystemExit(f"Source not found: {md_path}")
    pdf_name = os.path.splitext(md_filename)[0] + ".pdf"
    pdf_path = os.path.join(OUT_DIR, pdf_name)

    html = md_to_html(md_path, title)
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".html", delete=False, encoding="utf-8"
    ) as tmp:
        tmp.write(html)
        html_path = tmp.name
    try:
        html_to_pdf(EDGE, html_path, pdf_path)
    finally:
        try:
            os.remove(html_path)
        except OSError:
            pass

    size = os.path.getsize(pdf_path)
    print(f"  {md_filename} -> {pdf_path} ({size:,} bytes)")


EDGE = find_edge()
os.makedirs(OUT_DIR, exist_ok=True)
print(f"Edge: {EDGE}")
print(f"Output dir: {OUT_DIR}")
print()
build("TRAINER_GUIDE.md", "Pig Training - Trainer Guide")
build("REFERENCE_CARD.md", "Pig Training - Reference Card")
print()
print("Done.")
