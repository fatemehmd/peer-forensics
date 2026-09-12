"""Export the current Markdown report to a self-contained, printable HTML file."""

import base64
import hashlib
from pathlib import Path

from markdown_it import MarkdownIt


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "NARRATIVE_REPORT.md"
OUTPUT = ROOT / "reports" / "NARRATIVE_REPORT.html"

raw = SOURCE.read_bytes()
parser = MarkdownIt("commonmark", {"html": False}).enable("table")
tokens = parser.parse(raw.decode("utf-8"))
figures = 0
for token in tokens:
    for child in token.children or []:
        if child.type == "image":
            path = (ROOT / child.attrGet("src")).resolve()
            assert path.is_file() and path.suffix == ".png", path
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            child.attrSet("src", "data:image/png;base64," + encoded)
            figures += 1
        elif child.type == "link_open":
            href = child.attrGet("href")
            if href and not href.startswith(("https://", "http://", "#")):
                child.attrSet("href", (ROOT / href).resolve().as_uri())

body = parser.renderer.render(tokens, parser.options, {})
html = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Completion pressure and permissive interpretations of a fixed rule</title>
<style>
body { max-width: 820px; margin: 40px auto; padding: 0 24px; color: #222b31;
       font: 16px/1.5 Georgia, serif; background: white; }
h1, h2, h3 { font-family: Arial, sans-serif; line-height: 1.25; letter-spacing: 0; }
h1 { font-size: 28px; } h2 { font-size: 22px; margin-top: 32px; }
h3 { font-size: 18px; margin-top: 26px; }
p, li { overflow-wrap: anywhere; }
img { width: 100%; height: auto; }
table { border-collapse: collapse; width: 100%; font-size: 14px; margin: 20px 0; }
th, td { border-bottom: 1px solid #dfe4e8; text-align: left; padding: 9px; }
th { background: #f2f5f7; font-family: Arial, sans-serif; }
blockquote { border-left: 3px solid #2866a6; margin: 20px 0; padding-left: 18px; }
pre { white-space: pre-wrap; padding: 12px; background: #f2f5f7; font-size: 13px; }
code { overflow-wrap: anywhere; } a { color: #2866a6; }
@media print {
  body { max-width: none; margin: 0; padding: 0; font-size: 10.5pt; }
  h1 { font-size: 21pt; } h2 { font-size: 16pt; } h3 { font-size: 13pt; }
  h1, h2, h3 { break-after: avoid; } img, table, blockquote { break-inside: avoid; }
  table { font-size: 9pt; } a { color: inherit; text-decoration: none; }
  @page { margin: 20mm; }
}
</style></head><body>
""" + body + "\n</body></html>\n"
OUTPUT.write_text(html, encoding="utf-8")
print(f"Exported {OUTPUT}; {figures} embedded figures.")
print(f"Source SHA256: {hashlib.sha256(raw).hexdigest()}")
print("Local evidence links require a shared repository to be usable by external reviewers.")
