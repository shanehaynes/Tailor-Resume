"""`rc new-app`: scaffold applications/YYYY-MM-DD-company-role/ and save the posting verbatim."""
import datetime as dt
import html.parser
import re
import urllib.request
from pathlib import Path

import yaml

from rc import app as apps

MIN_TEXT = 600  # less than this from a URL usually means a JS-rendered page


class FetchFailed(Exception):
    pass


class _Text(html.parser.HTMLParser):
    SKIP = {"script", "style", "noscript", "svg", "head"}
    BLOCK = {"p", "div", "li", "br", "h1", "h2", "h3", "h4", "tr", "section", "ul", "ol"}

    def __init__(self):
        super().__init__()
        self.out, self.skip = [], 0

    def handle_starttag(self, tag, attrs):
        self.skip += tag in self.SKIP
        if tag in self.BLOCK:
            self.out.append("\n")
        if tag == "li":
            self.out.append("- ")

    def handle_endtag(self, tag):
        self.skip -= tag in self.SKIP and self.skip > 0

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data)


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (tailor-resume)"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            raw = r.read().decode(r.headers.get_content_charset() or "utf-8", "replace")
    except Exception as e:
        raise FetchFailed(f"fetch failed: {e}") from e
    p = _Text()
    p.feed(raw)
    text = re.sub(r"[ \t]+", " ", "".join(p.out))
    text = re.sub(r"\n\s*\n+", "\n\n", text).strip()
    if len(text) < MIN_TEXT:
        raise FetchFailed(f"only {len(text)} chars of text came back (JS-rendered page?)")
    return text


def slugify(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")


def new_app(company: str, role: str, url: str | None = None, text: str | None = None,
            date: dt.date | None = None, root: Path | None = None) -> Path:
    if text is None:
        if not url:
            raise ValueError("need a URL or the posting text")
        text = fetch(url)
    date = date or dt.date.today()
    d = (root or apps.APPLICATIONS) / f"{date.isoformat()}-{slugify(company)}-{slugify(role)}"
    if d.exists():
        raise FileExistsError(f"{d} already exists")
    d.mkdir(parents=True)
    header = f"<!-- captured {date.isoformat()}{' from ' + url if url else ''}; verbatim below -->\n\n"
    (d / "posting.md").write_text(header + text.strip() + "\n")
    (d / "meta.yaml").write_text(yaml.safe_dump(
        {"company": company, "role": role, "url": url, "captured": date.isoformat(),
         "status": "drafting", "deadline": None}, sort_keys=False))
    return d
