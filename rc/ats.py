"""ATS round-trip (spec §6): what a parser reads back out of the PDF.

Fails on ligature or replacement glyphs, on any bullet or line whose text doesn't
come back contiguous and in order (interleaved reading order), and on missing
contact info. Reports keyword coverage for the exact phrases in analysis.md.

Uses only pdftotext behavior that is stable across poppler versions (CI runs
24.02, macOS brew 26.x): characters present, and order after whitespace collapse.
"""
import re
import subprocess
from pathlib import Path

BAD_GLYPHS = {"ﬀ": "ff ligature", "ﬁ": "fi ligature", "ﬂ": "fl ligature",
              "ﬃ": "ffi ligature", "ﬄ": "ffl ligature", "ﬅ": "st ligature",
              "ﬆ": "st ligature", "�": "replacement char", "­": "soft hyphen"}


def pdftotext(pdf: Path, mode: str) -> str:
    return subprocess.run(["pdftotext", f"-{mode}", str(pdf), "-"],
                          capture_output=True, text=True, check=True).stdout


def norm(s: str) -> str:
    return " ".join(s.split())


def keyword_pattern(phrase: str) -> re.Pattern:
    """Whole-word, case-insensitive match after norm(). The phrase can't start
    mid-word ("ERP" misses "PowerPoint"). It may end in an inflection (s, es, d,
    ed, ing: "launch" hits "launched") unless its last word is an acronym ("AI"
    misses "aid"). Hyphens and spaces are boundaries, so "AI" hits "AI-powered"."""
    p = norm(phrase)
    left = r"(?<![a-z0-9])" if p[:1].isalnum() else ""
    right = ""
    if p[-1:].isalnum():
        acronym = re.findall(r"[A-Za-z0-9]+", p)[-1].isupper()
        right = ("" if acronym else r"(?:s|es|d|ed|ing)?") + r"(?![a-z0-9])"
    return re.compile(left + re.escape(p.lower()) + right)


def _expected(resolved: dict) -> list[tuple[str, str]]:
    """(id, text) for every bullet and line, in document order."""
    out = []
    for s in resolved["sections"]:
        for e in s.get("entries", []):
            for r in e["roles"]:
                out += [(b["id"], b["text"]) for b in r.get("bullets", [])]
        out += [(b["id"], b["text"]) for b in s.get("bullets", [])]
        out += [(l["id"], f"{l['label']}: {l['text']}") for l in s.get("lines", [])]
    return out


def parse_analysis(path: Path) -> list[dict]:
    """Rows of the analysis.md matrix: requirement | priority | exact phrases |
    matched ledger ids | strength | notes. Phrases are "double-quoted" in their cell."""
    if not path.exists():
        return []
    rows, header = [], None
    for line in path.read_text().splitlines():
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if header is None:
            header = [c.lower() for c in cells]
            continue
        if set("".join(cells)) <= set("-: "):
            continue
        row = dict(zip(header, cells))
        ids = [i.strip(" `") for i in re.split(r"[,;]", row.get("matched ledger ids", ""))]
        rows.append({"requirement": row.get("requirement", ""),
                     "phrases": re.findall(r'"([^"]+)"', row.get("exact phrases", "")),
                     "ids": [i for i in ids if i and i not in ("-", "—", "none")]})
    return rows


def check(pdf: Path, resolved: dict, analysis: Path | None = None) -> dict:
    raw, layout = pdftotext(pdf, "raw"), pdftotext(pdf, "layout")
    flat = norm(raw)
    failures = []
    for mode, text in (("raw", raw), ("layout", layout)):
        for ch, name in BAD_GLYPHS.items():
            if ch in text:
                failures.append(f"{mode}: {name} (U+{ord(ch):04X}) in text layer")
    for item in resolved["contact"]["items"]:
        if norm(item["text"]) not in flat:
            failures.append(f"contact: {item['text']!r} not extracted")
    if norm(resolved["contact"]["name"]).upper() not in flat.upper():
        failures.append("contact: name not extracted")
    pos = 0
    for id_, text in _expected(resolved):
        i = flat.find(norm(text), pos)
        if i < 0:
            where = "out of order" if norm(text) in flat else "not contiguous (interleaved)"
            failures.append(f"{id_}: text {where}")
        else:
            pos = i + len(norm(text))
    keywords = []
    if analysis:
        low = flat.lower()
        for row in parse_analysis(analysis):
            for ph in row["phrases"]:
                status = ("present" if keyword_pattern(ph).search(low)
                          else "wording gap" if row["ids"] else "ledger gap")
                keywords.append({"phrase": ph, "requirement": row["requirement"], "status": status})
    return {"ok": not failures, "failures": failures, "keywords": keywords}
