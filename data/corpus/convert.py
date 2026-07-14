import sys
from pathlib import Path

from bs4 import BeautifulSoup
import html2text

def convert(html_path: Path) -> None:
    soup = BeautifulSoup(html_path.read_text(encoding="utf-8"), "html.parser")
    main = soup.find("main") or soup.find("article") or soup.body
    for tag in main.find_all(["nav", "script", "style", "aside", "form", "noscript"]):
        tag.decompose()
    h = html2text.HTML2Text()
    h.ignore_links = True
    h.ignore_images = True
    h.body_width = 0
    md = h.handle(str(main))
    out = html_path.with_suffix(".md")
    out.write_text(md, encoding="utf-8")
    print(f"{out.name}: {len(md)} chars")

for p in sorted(Path(".").glob("*.html")):
    convert(p)