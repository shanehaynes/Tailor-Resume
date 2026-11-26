"""Phase 4: fit checker, bullet->id mapping, solver, determinism."""
import copy
import json
from pathlib import Path

import pytest
import yaml

from rc import fit
from rc.paths import ROOT

GOLDEN = ROOT / "tests" / "golden" / "base.resolved.yaml"
LINES = ROOT / "tests" / "golden" / "base.lines.json"
WORK = ROOT / "build" / "test-fit"

ONE = "Mapped yard moves at two terminals to cut trailer search time"
THREE = ("Rebuilt the cross-dock labor plan from twelve months of scan data, matching shift starts to inbound arrival "
         "waves at 6 terminals; overtime fell 14%, average trailer turn time improved by 40 minutes, and peak-season "
         "temporary staffing dropped from 90 to 55 workers without a single missed carrier cutoff")
ORPHAN = ("Standardized pallet build rules for outbound retail orders and trained night-shift loaders on them; "
          "freight damage claims fell 27% within a single quarter")
FULL = ("Moved slow-moving SKUs to upper rack levels after a velocity study of every pick location in the main "
        "warehouse, shortening average picker travel per order and freeing two aisles of prime floor slots for the "
        "fastest movers")


def doc(bullets: list[tuple[str, str]], layout=None) -> dict:
    g = yaml.safe_load(GOLDEN.read_text())
    g["layout"] = layout or {}
    g["sections"] = [{"heading": "Projects", "bullets": [{"id": i, "text": t} for i, t in bullets]}]
    return g


def run(resolved: dict, name: str) -> fit.Measurement:
    WORK.mkdir(parents=True, exist_ok=True)
    src = WORK / f"{name}.resolved.yaml"
    src.write_text(yaml.safe_dump(resolved))
    return fit.measure(src, WORK / f"{name}.pdf")


def by_id(m):
    return {it.id: it for it in m.items}


def test_mapping_assigns_lines_to_the_right_ids():
    m = run(doc([("c", THREE), ("a", ONE), ("d", ORPHAN), ("b", FULL)]), "mapping")
    got = {k: v.n_lines for k, v in by_id(m).items()}
    assert got == {"a": 1, "b": 2, "c": 3, "d": 2}
    assert [it.id for it in m.items] == ["c", "a", "d", "b"]


def test_three_line_bullet_fails_with_cut_estimate():
    fails = fit.check(run(doc([("x", THREE)]), "three"))
    f = [f for f in fails if f.id == "x"]
    assert len(f) == 1 and f[0].rule == "lines"
    assert f[0].message.startswith("3 lines -> cut ~")


def test_orphan_detected_with_deltas():
    m = run(doc([("x", ORPHAN)]), "orphan")
    assert 0.30 < by_id(m)["x"].last_fill < 0.33
    f = [f for f in fit.check(m) if f.id == "x"][0]
    assert f.rule == "orphan"
    assert "last line 33% full -> cut ~" in f.message and "or add ~" in f.message


def test_single_line_bullet_is_never_an_orphan():
    assert not [f for f in fit.check(run(doc([("x", "Short")]), "short")) if f.id == "x"]


def test_page_two_overflow():
    m = run(doc([(f"b{i}", FULL) for i in range(40)]), "overflow")
    assert m.pages == 2 and m.overflow_lines > 0
    assert by_id(m)["b39"].page == 2
    assert any(f.rule == "pages" for f in fit.check(m))


def test_underfill_reports_lines_to_add():
    m = run(doc([("x", ONE)]), "underfill")
    f = [f for f in fit.check(m) if f.rule == "fill"][0]
    assert "add ~" in f.message


def test_golden_line_counts_are_deterministic():
    """Recorded once (tests/golden/base.lines.json); must match on every machine and in CI."""
    m = run(yaml.safe_load(GOLDEN.read_text()), "golden")
    got = {it.id: [it.n_lines, round(it.last_fill, 2)] for it in m.items}
    assert got == json.loads(LINES.read_text())
    assert round(m.fill, 3) == 0.871


def test_solver_fixes_base_within_bounds():
    s = fit.solve(yaml.safe_load(GOLDEN.read_text()), WORK / "solve")
    assert s.ok and not s.failures
    assert s.measurement.pages == 1 and s.measurement.fill >= 0.95
    L = s.layout
    assert 10 <= L["font_size"] <= 11 and min(L["margin_x"], L["margin_top"], L["margin_bottom"]) >= 0.5
    for k, (_, lo, hi) in fit.SPACING.items():
        assert lo <= L[k] <= hi, k


def test_solver_prefers_spacing_when_it_suffices():
    bullets = [(f"b{i}", FULL) for i in range(22)]
    s = fit.solve(doc(bullets), WORK / "solve-spacing")
    assert s.ok, s.note
    assert s.layout["font_size"] == 10.5 and s.layout["margin_x"] == 0.6


def test_solver_says_when_only_content_can_fix():
    s = fit.solve(doc([(f"b{i}", FULL) for i in range(45)]), WORK / "solve-overflow")
    assert not s.ok and "only content can fix" in s.note


def test_wrapped_degree_line_fails():
    g = yaml.safe_load(GOLDEN.read_text())
    bs = g["sections"][0]["entries"][1]["roles"][0]
    bs["detail"] = ("Supply Chain Management (Transportation and Logistics Concentration); "
                    "Economics Minor; Quantitative Methods Certificate")
    fails = fit.check(run(g, "degree-wrap"))
    assert [f.id for f in fails if f.rule == "title"] == ["edu-brookfield:title0"]


def test_base_titles_are_single_lines():
    m = run(yaml.safe_load(GOLDEN.read_text()), "titles")
    titles = [it for it in m.items if it.kind == "title"]
    assert len(titles) == 5 and all(it.n_lines == 1 for it in titles)
