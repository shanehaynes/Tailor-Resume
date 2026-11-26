"""Fit checker and lever solver (spec §3, §6). Every number comes from the rendered
PDF (pdfplumber glyph positions) and Typst's own bullet marks (templates/resume.typ),
never from estimates.

Bullet -> id mapping: the template wraps each bullet's text in two metadata marks
(start: top of first line; end: bottom of last line). A bullet's glyphs are the
ones inside that band, right of the start mark. No reliance on ordering.
"""
import json
import math
import statistics
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import yaml

from rc.paths import ROOT, typst_eval_args
from rc.render import TEMPLATE, render

CONSTRAINTS = {"min_fill": 0.95, "max_bullet_lines": 2, "min_last_line": 0.35}
FILL_TARGET = 0.985  # the solver aims here; anything >= min_fill on one page passes

# Levers: (default, min, max). Defaults are the template's look (reference/measurements.md).
SPACING = {"leading": (2.7, 1.8, 4.0), "bullet_gap": (0.0, 0.0, 2.0), "role_gap": (1.0, 0.5, 3.0),
           "entry_gap": (6.0, 3.0, 10.0), "section_gap": (10.0, 6.0, 14.0), "line_gap": (1.0, 0.0, 2.0)}
MARGIN_V = {"margin_top": (0.6458, 0.5, 0.75), "margin_bottom": (0.5, 0.5, 0.75)}
MARGIN_X = [0.6, 0.55, 0.65, 0.5, 0.7, 0.75]   # inches, nearest the default first; floor 0.5
FONT = [10.5, 10.25, 10.75, 10.0, 11.0]        # pt, nearest the default first; 10-11


@dataclass
class Line:
    baseline: float
    x0: float
    x1: float      # right edge of the last non-space glyph
    chars: int     # non-space glyphs
    width: float   # sum of non-space glyph widths


@dataclass
class Item:
    id: str
    kind: str      # bullet | line
    page: int
    col_x0: float
    col_x1: float
    lines: list[Line] = field(default_factory=list)

    @property
    def n_lines(self) -> int:
        return len(self.lines)

    @property
    def last_fill(self) -> float:
        return (self.lines[-1].x1 - self.col_x0) / (self.col_x1 - self.col_x0) if self.lines else 0.0

    @property
    def avg_char(self) -> float:
        n = sum(l.chars for l in self.lines)
        return sum(l.width for l in self.lines) / n if n else 5.0


@dataclass
class Measurement:
    pages: int
    fill: float            # page 1: (content bottom - top margin) / usable height
    usable: float          # usable height, pt
    pitch: float           # median baseline-to-baseline distance inside bullets, pt
    overflow_lines: int    # text lines on pages after the first
    items: list[Item]
    layout: dict


@dataclass
class Failure:
    id: str
    rule: str      # pages | fill | lines | orphan | title
    message: str


def _rel(path: Path) -> str:
    return "/" + Path(path).resolve().relative_to(ROOT).as_posix()


def _introspect(resolved: Path) -> dict:
    expr = "(marks: query(<rc-mark>).map(m => m.value), geometry: query(<rc-geometry>).first().value)"
    r = subprocess.run(typst_eval_args(TEMPLATE, expr, {"resolved": _rel(resolved)}),
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"typst eval failed:\n{r.stderr}")
    return json.loads(r.stdout)


def _lines(chars, x_min, top, bottom) -> list[Line]:
    rows: dict[float, list] = {}
    for c in chars:
        if c["x0"] >= x_min - 0.5 and c["top"] >= top - 0.5 and c["bottom"] <= bottom + 0.5:
            rows.setdefault(round(c["baseline"], 1), []).append(c)
    out = []
    for base in sorted(rows):
        ink = [c for c in rows[base] if not c["text"].isspace()]
        if ink:
            out.append(Line(base, min(c["x0"] for c in ink), max(c["x1"] for c in ink),
                            len(ink), sum(c["x1"] - c["x0"] for c in ink)))
    return out


def measure(resolved: Path, pdf: Path) -> Measurement:
    """Render a resolved file and measure it."""
    render(resolved, pdf)
    meta = _introspect(resolved)
    geo = meta["geometry"]
    with pdfplumber.open(pdf) as doc:
        pages = []
        for p in doc.pages:
            chars = [dict(c, baseline=p.height - c["matrix"][5]) for c in p.chars]
            pages.append(chars)
    marks: dict[str, dict] = {}
    for m in meta["marks"]:
        marks.setdefault(m["id"], {"kind": m["kind"]})[m["edge"]] = m
    items = []
    for id_, mk in marks.items():
        s, e = mk["start"], mk["end"]
        it = Item(id_, mk["kind"], s["page"], s["x"], geo["text_right"])
        if s["page"] == e["page"]:
            it.lines = _lines(pages[s["page"] - 1], s["x"], s["y"], e["y"])
        else:  # split across pages
            it.lines = (_lines(pages[s["page"] - 1], s["x"], s["y"], geo["page_height"])
                        + _lines(pages[e["page"] - 1], s["x"], 0, e["y"]))
        items.append(it)
    usable = geo["page_height"] - geo["margin_top"] - geo["margin_bottom"]
    bottom = max((c["bottom"] for c in pages[0]), default=geo["margin_top"])
    diffs = [b.baseline - a.baseline for it in items for a, b in zip(it.lines, it.lines[1:])]
    overflow = len({round(c["baseline"], 1) for p in pages[1:] for c in p})
    layout = yaml.safe_load(Path(resolved).read_text()).get("layout", {})
    return Measurement(len(pages), (bottom - geo["margin_top"]) / usable, usable,
                       statistics.median(diffs) if diffs else 13.2, overflow, items, layout)


def check(m: Measurement, constraints: dict | None = None) -> list[Failure]:
    c = {**CONSTRAINTS, **(constraints or {})}
    out = []
    if m.pages > 1:
        out.append(Failure("page", "pages", f"{m.pages} pages: {m.overflow_lines} line(s) overflow "
                                            f"-> cut ~{m.overflow_lines} line(s)"))
    elif m.fill < c["min_fill"]:
        need = math.ceil((c["min_fill"] - m.fill) * m.usable / m.pitch)
        out.append(Failure("page", "fill", f"page fill {m.fill:.1%} < {c['min_fill']:.0%} "
                                           f"-> add ~{need} line(s) of content"))
    for it in m.items:
        if it.kind == "title" and it.n_lines > 1:
            extra = sum(l.chars + 1 for l in it.lines[1:])
            out.append(Failure(it.id, "title", f"title/degree line wraps to {it.n_lines} lines "
                                              f"-> cut ~{extra} chars or use a shorter variant"))
        if it.kind != "bullet":
            continue
        if it.n_lines > c["max_bullet_lines"]:
            extra = sum(l.chars + 1 for l in it.lines[c["max_bullet_lines"]:])
            out.append(Failure(it.id, "lines", f"{it.n_lines} lines -> cut ~{extra} chars"))
        elif it.n_lines >= 2 and it.last_fill < c["min_last_line"]:
            cut = it.lines[-1].chars + 1
            width = it.col_x1 - it.col_x0
            add = math.ceil((c["min_last_line"] * width - (it.lines[-1].x1 - it.col_x0)) / it.avg_char)
            out.append(Failure(it.id, "orphan", f"{it.n_lines} lines, last line {it.last_fill:.0%} full "
                                                f"-> cut ~{cut} chars or add ~{add}"))
    return out


# --- solver ------------------------------------------------------------------

def _interp(levers: dict, t: float) -> dict:
    """t in [-1, 1]: -1 = every lever at its min, 0 = default, 1 = max."""
    return {k: round(d + t * ((hi - d) if t > 0 else (d - lo)), 2) for k, (d, lo, hi) in levers.items()}


@dataclass
class Solution:
    ok: bool
    layout: dict
    measurement: Measurement
    failures: list[Failure]
    note: str
    trials: int = 0


class _Trials:
    def __init__(self, resolved: dict, workdir: Path, constraints: dict | None):
        self.resolved, self.workdir, self.constraints, self.n = resolved, workdir, constraints, 0
        workdir.mkdir(parents=True, exist_ok=True)

    def __call__(self, layout: dict) -> tuple[Measurement, list[Failure]]:
        self.n += 1
        src = self.workdir / "trial.resolved.yaml"
        src.write_text(yaml.safe_dump({**self.resolved, "layout": layout}, sort_keys=False, allow_unicode=True))
        m = measure(src, self.workdir / "trial.pdf")
        return m, check(m, self.constraints)


def _largest(ok, lo: float, hi: float, steps: int = 10) -> float | None:
    """Largest x in [lo, hi] with ok(x), assuming ok is true below some threshold."""
    if not ok(lo):
        return None
    if ok(hi):
        return hi
    for _ in range(steps):
        mid = (lo + hi) / 2
        lo, hi = (mid, hi) if ok(mid) else (lo, mid)
    return math.floor(lo * 100) / 100


def solve(resolved: dict, workdir: Path, constraints: dict | None = None) -> Solution:
    """Lever order (spec §3): spacing -> margins (vertical, then horizontal) -> font size.
    Content is never touched; when only content can fix it, say so with the deltas."""
    c = {**CONSTRAINTS, **(constraints or {})}
    trial = _Trials(resolved, workdir, constraints)
    best = None  # fewest line failures; earliest (nearest the defaults) wins ties
    for fs in FONT:
        for mx in MARGIN_X:
            horiz = {"font_size": fs, "margin_x": mx}
            lay = lambda t, u: {**horiz, **_interp(SPACING, t), **_interp(MARGIN_V, u)}
            m, fails = trial(lay(0, 0))
            n_line = sum(f.rule in ("lines", "orphan", "title") for f in fails)
            if best is None or n_line < best[0]:
                best = (n_line, m, fails)
            if n_line:
                continue  # line breaks depend only on font and margin_x
            fits = lambda t, u: (lambda r: r[0].pages == 1 and r[0].fill <= FILL_TARGET)(trial(lay(t, u)))
            u = 0.0
            t = _largest(lambda x: fits(x, 0.0), -1.0, 1.0)
            if t is None:  # overflows even at tightest spacing: shrink vertical margins
                u = _largest(lambda x: fits(-1.0, x), -1.0, 0.0)
                t = -1.0
                if u is None:
                    continue
            elif t == 1.0:  # still under target at loosest spacing: grow vertical margins
                u = _largest(lambda x: fits(1.0, x), 0.0, 1.0) or 0.0
            m, fails = trial(lay(t, u))
            if not fails:
                moved = [n for n, v in (("spacing", t), ("vertical margins", u)) if v]
                moved += [n for n, v in (("margin_x", mx != MARGIN_X[0]), ("font size", fs != FONT[0])) if v]
                return Solution(True, lay(t, u), m, [], "levers moved: " + (", ".join(moved) or "none"), trial.n)
    _, m, fails = best
    return Solution(False, m.layout, m, fails,
                    "only content can fix this: no lever combination within bounds passes; "
                    f"closest (font {m.layout['font_size']}pt, margin_x {m.layout['margin_x']}in) shown", trial.n)


def table(m: Measurement, failures: list[Failure]) -> str:
    bad = {f.id: f for f in failures}
    rows = [f"{'id':38} {'lines':>5} {'last':>5}  verdict"]
    for it in m.items:
        if it.kind != "bullet":
            continue
        f = bad.get(it.id)
        rows.append(f"{it.id:38} {it.n_lines:>5} {it.last_fill:>5.0%}  {f.message if f else 'ok'}")
    rows.append(f"pages {m.pages}  fill {m.fill:.1%}  levers {json.dumps(m.layout, sort_keys=True)}")
    rows += [f"FAIL {f.id}: {f.message}" for f in failures if f.rule == "title"]
    rows += [f"FAIL {f.message}" for f in failures if f.id == "page"]
    return "\n".join(rows)


def to_report(m: Measurement, failures: list[Failure]) -> dict:
    return {
        "ok": not failures,
        "pages": m.pages,
        "fill": round(m.fill, 4),
        "levers": m.layout,
        "bullets": [{"id": it.id, "lines": it.n_lines, "last_line_fill": round(it.last_fill, 3)}
                    for it in m.items if it.kind == "bullet"],
        "failures": [{"id": f.id, "rule": f.rule, "message": f.message} for f in failures],
    }
