"""Cover letter (spec §7): parse cover-letter.md, check it against the ledger, render.

cover-letter.md:
    ---
    date: October 5, 2026
    recipient: [Acme Corp Recruiting]
    acknowledge: {dock-scheduling.detention: "owner 2026-10-05: ..."}   # single facts only
    ---
    Paragraph text. <!-- ledger: route-optimization.miles-cut, route-ledger.what -->
    <!-- source: https://example.com/page | "the exact sentence relied on" -->

Each paragraph cites the ledger facts it uses (`acc.fact`, `edu-id.fact`,
`additional.fact`). Company claims cite a source URL with a verbatim quote.
Every number in a paragraph must appear in its cited facts or in a source quote.
Comment-only blocks hold letter-wide sources and research notes.
"""
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import yaml

from rc import ledger, resolve
from rc.paths import ROOT, typst_compile_args

TEMPLATE = ROOT / "templates" / "cover-letter.typ"
COMMENT = re.compile(r"<!--(.*?)-->", re.S)
SOURCE = re.compile(r'^\s*source:\s*(\S+)\s*(?:\|\s*"(.*)")?\s*$', re.S)


@dataclass
class Para:
    text: str
    facts: list[str] = field(default_factory=list)
    sources: list[tuple[str, str]] = field(default_factory=list)


@dataclass
class Letter:
    front: dict
    paras: list[Para]
    sources: list[tuple[str, str]]  # letter-wide


def parse(path: Path) -> Letter:
    raw = Path(path).read_text()
    front = {}
    if raw.startswith("---"):
        _, fm, raw = raw.split("---", 2)
        front = yaml.safe_load(fm) or {}
    paras, sources = [], []
    for block in re.split(r"\n\s*\n", raw.strip()):
        comments = COMMENT.findall(block)
        text = COMMENT.sub("", block).strip()
        p = Para(text)
        for c in comments:
            c = c.strip()
            if c.startswith("ledger:"):
                p.facts += [r.strip() for r in c[len("ledger:"):].split(",") if r.strip()]
            elif m := SOURCE.match(c):
                p.sources.append((m.group(1), m.group(2) or ""))
        if text:
            paras.append(p)
        else:
            sources += p.sources
    return Letter(front, paras, sources)


def fact_index(data: dict) -> dict[str, dict]:
    idx = {}
    for acc in ledger.accomplishments(data):
        idx.update({f"{acc.id}.{fid}": f for fid, f in acc.facts.items()})
    for edu in data["education"]:
        idx.update({f"{edu['id']}.{f['id']}": f for f in edu["facts"]})
    idx.update({f"additional.{f['id']}": f for f in ledger.additional_facts(data)})
    return idx


def check(letter: Letter, data: dict) -> dict:
    idx = fact_index(data)
    ack = letter.front.get("acknowledge") or {}
    failures, warnings = [], []
    quotes = [q for _, q in letter.sources]
    for i, p in enumerate(letter.paras, 1):
        where = f"paragraph {i}"
        have = set()
        for ref in p.facts:
            f = idx.get(ref)
            if f is None:
                failures.append(f"{where}: unknown ledger fact {ref!r}")
                continue
            if f["status"] in ("conflict", "retired"):
                failures.append(f"{where}: {ref} is {f['status']}")
            elif f["status"] == "single" and not ack.get(ref):
                failures.append(f"{where}: {ref} is single; needs `acknowledge:` with the owner's words")
            have |= ledger.numbers(f["claim"])
        for url, q in p.sources:
            if not url.startswith("https://"):
                failures.append(f"{where}: source {url!r} is not an https URL")
            if not q:
                failures.append(f"{where}: source {url} has no verbatim quote")
        for q in quotes + [q for _, q in p.sources]:
            have |= ledger.numbers(q)
        if missing := ledger.numbers(p.text) - have:
            failures.append(f"{where}: numbers {sorted(missing)} not in its cited facts or source quotes")
        if len(p.text.split()) > 25 and not p.facts and not p.sources:
            warnings.append(f"{where}: {len(p.text.split())} words with no ledger or source citation")
    words = sum(len(p.text.split()) for p in letter.paras)
    return {"ok": not failures, "failures": failures, "warnings": warnings, "words": words}


def resolved(letter: Letter, data: dict) -> dict:
    contact = resolve.resolve({"sections": []}, data)["contact"]
    return {"contact": contact, "date": str(letter.front.get("date", "")),
            "recipient": letter.front.get("recipient", []),
            "paragraphs": [p.text for p in letter.paras]}


def render(letter: Letter, data: dict, work: Path, out: Path) -> int:
    """Render to PDF; return the page count."""
    work.mkdir(parents=True, exist_ok=True)
    src = work / "cover.resolved.yaml"
    src.write_text(yaml.safe_dump(resolved(letter, data), sort_keys=False, allow_unicode=True, width=1000))
    rel = "/" + src.resolve().relative_to(ROOT).as_posix()
    r = subprocess.run(typst_compile_args(TEMPLATE, out, {"resolved": rel}), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"typst failed:\n{r.stderr}")
    with pdfplumber.open(out) as pdf:
        return len(pdf.pages)
