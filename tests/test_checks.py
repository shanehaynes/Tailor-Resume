"""Phase 4: ATS round-trip, truth check, gate."""
import argparse
import copy
import json
from pathlib import Path

import pytest
import yaml

from rc import app as apps
from rc import ats, cli, ledger, truth
from rc.paths import ROOT
from rc.render import render

GOLDEN = ROOT / "tests" / "golden" / "base.resolved.yaml"
FIXTURE_LEDGER = Path(__file__).parent / "fixtures" / "ledger-min.yaml"
EXAMPLE = ROOT / "ledger" / "example.yaml"


@pytest.fixture(scope="module")
def golden():
    pdf = render(GOLDEN, ROOT / "build" / "test-checks" / "golden.pdf")
    return pdf, yaml.safe_load(GOLDEN.read_text())


# --- ATS ---------------------------------------------------------------------

def test_ats_passes_golden(golden):
    pdf, res = golden
    r = ats.check(pdf, res)
    assert r["ok"], r["failures"]


def test_ats_detects_out_of_order(golden):
    pdf, res = golden
    res = copy.deepcopy(res)
    b = res["sections"][1]["entries"][0]["roles"][0]["bullets"]
    b[0], b[1] = b[1], b[0]
    assert any("out of order" in f for f in ats.check(pdf, res)["failures"])


def test_ats_detects_missing_or_interleaved_text(golden):
    pdf, res = golden
    res = copy.deepcopy(res)
    res["sections"][2]["bullets"][0]["text"] = "Route Ledger: something the PDF does not say"
    res["contact"]["items"].append({"text": "Tel: (000) 000-0000"})
    fails = ats.check(pdf, res)["failures"]
    assert any("route-ledger/base: text not contiguous" in f for f in fails)
    assert any("contact: 'Tel: (000) 000-0000'" in f for f in fails)


def test_ats_detects_ligature_glyph(golden, monkeypatch):
    # Ligatures are off in the template, so a clean render never forms one;
    # feed the detector a text layer that has one.
    pdf, res = golden
    real = ats.pdftotext
    monkeypatch.setattr(ats, "pdftotext", lambda p, mode: real(p, mode).replace("first", "\ufb01rst", 1))
    assert any("fi ligature" in f for f in ats.check(pdf, res)["failures"])


def test_ligature_codepoint_in_text_renders_but_fails_ats(tmp_path):
    """A ligature codepoint in source text (pasted wording) is not a render error:
    Typst draws a missing glyph and keeps U+FB01 in the text layer. The ATS check
    is what stops it shipping."""
    g = yaml.safe_load(GOLDEN.read_text())
    g["sections"][2]["bullets"][0]["text"] = "Route \ufb01nal"
    src = ROOT / "build" / "test-checks" / "lig.resolved.yaml"
    src.write_text(yaml.safe_dump(g, allow_unicode=True))
    pdf = render(src, tmp_path / "lig.pdf")
    assert any("fi ligature" in f for f in ats.check(pdf, g)["failures"])


def test_keyword_coverage(golden, tmp_path):
    pdf, res = golden
    a = tmp_path / "analysis.md"
    a.write_text("""| Requirement | Priority | Exact phrases | Matched ledger ids | Strength | Notes |
|---|---|---|---|---|---|
| Carrier management | must | "carrier scorecard", "S&OP planning" | carrier-scorecard | strong | |
| SQL | nice | "dbt" | — | gap | |
""")
    got = {k["phrase"]: k["status"] for k in ats.check(pdf, res, a)["keywords"]}
    assert got == {"carrier scorecard": "present", "S&OP planning": "wording gap", "dbt": "ledger gap"}


# --- truth -------------------------------------------------------------------

def sel(bullets, ack=None):
    s = {"sections": [{"heading": "Experience",
                       "entries": [{"employer": "acme", "roles": [{"role": "acme-dev", "bullets": bullets}]}]}]}
    if ack:
        s["acknowledge"] = ack
    return s


@pytest.fixture
def data():
    return ledger.load(FIXTURE_LEDGER)


def test_truth_clear_passes(data):
    assert truth.check(sel(["widget/clear"]), data)["ok"]


@pytest.mark.parametrize("ref", ["widget/needs-ack", "widget/proposed"])
def test_truth_needs_ack(data, ref):
    r = truth.check(sel([ref]), data)
    assert not r["ok"] and "needs the owner's acknowledgment" in r["failures"][0]
    r = truth.check(sel([ref], {ref: "owner confirmed 2026-10-05"}), data)
    assert r["ok"] and r["acknowledged"][0]["ref"] == ref


@pytest.mark.parametrize("ref", ["widget/blocked", "widget/retired"])
def test_truth_blocked_even_if_acknowledged(data, ref):
    r = truth.check(sel([ref], {ref: "please"}), data)
    assert not r["ok"] and "(blocked)" in r["failures"][0]


def test_truth_untraced_number(data):
    v = data["experience"][0]["roles"][0]["accomplishments"][0]["variants"][0]
    v["text"] += " in 9 days"
    assert any("numbers ['9']" in f for f in truth.check(sel(["widget/clear"]), data)["failures"])


def test_truth_warns_on_stale_ack_and_split_group(data):
    r = truth.check(sel(["widget/clear"], {"widget/needs-ack": "old"}), data)
    assert r["ok"]
    assert any("stale" in w for w in r["warnings"])
    assert any("group 'pair' selected without ['proposed']" in w for w in r["warnings"])


def test_truth_unknown_ref_fails(data):
    r = truth.check(sel(["widget/ghost"]), data)
    assert not r["ok"] and r["failures"][0].startswith("resolve:")


def test_truth_on_example_selection_flags_what_shipped():
    """The example resume as shipped would now fail: conflict and retired wording,
    and a single fact nobody acknowledged."""
    s = yaml.safe_load((Path(__file__).parent / "fixtures" / "example.selection.yaml").read_text())
    fails = truth.check(s, ledger.load(EXAMPLE))["failures"]
    assert any(f.startswith("carrier-scorecard/base") and "conflict (blocked)" in f for f in fails)
    assert any(f.startswith("cross-dock/base") and "(blocked)" in f for f in fails)
    assert any(f.startswith("edu-brookfield/degree:base") and "(blocked)" in f for f in fails)
    assert any(f.startswith("edu-brookfield/case-comp") and "needs the owner's acknowledgment" in f for f in fails)


# --- gate --------------------------------------------------------------------

CLEAN = {
    "contact": ["phone", "email", "github", "linkedin"],
    "sections": [
        {"heading": "Education", "entries": [
            {"education": "edu-northgate", "lines": [{"facts": ["fellowship", "class-rep", "gmat"], "sep": "; "},
                                                     {"facts": ["club-lead", "clubs"], "sep": ", "}]},
            {"education": "edu-brookfield", "degree_variant": "compact",
             "lines": [{"facts": ["honors"], "sep": "; "}], "bullets": ["brookfield-capstone/adopted"]}]},
        {"heading": "Professional Experience", "entries": [{"employer": "harborview", "roles": [
            {"role": "hv-senior-analyst", "bullets": ["route-optimization/base", "dock-scheduling/base",
                                                      "carrier-scorecard/reviews", "carrier-rfp/base"]},
            {"role": "hv-analyst", "bullets": ["inventory-forecast/base", "kpi-dashboard/base"]},
            {"role": "hv-coordinator", "bullets": ["cross-dock/half"]}]}]},
        {"heading": "Projects", "bullets": [{"ref": "route-ledger/header", "link": True}, "route-ledger/detail-stack"]},
        {"heading": "Additional Information", "lines": [
            {"label": "Awards", "facts": ["ops-award"]},
            {"label": "Certifications", "facts": ["lean-green", "cpr"]},
            {"label": "Technical Skills", "skills": [
                ["Python", "SQL", "R"],
                {"label": "Optimization", "items": ["Mixed-integer programming", "Demand forecasting", "Simulation"]},
                ["Tableau", "Power BI", "DuckDB"], {"label": "Operations", "items": ["WMS", "TMS", "Lean"]}]},
            {"label": "Languages", "facts": ["english", "portuguese"]},
            {"label": "Volunteering", "facts": ["food-bank"]},
            {"label": "Other Interests",
             "interests": ["Trail running", "film photography", "chess", "project:field-notes"]}]},
    ],
    "acknowledge": {"edu-brookfield/degree:compact": "test fixture"},
}


@pytest.fixture
def example_ledger(monkeypatch):
    """Commands that read the default ledger (the gate, fit, status) read the example instead."""
    monkeypatch.setattr(ledger.load, "__defaults__", (EXAMPLE,))


def _gate(write: bool = False) -> int:
    return cli.cmd_gate(argparse.Namespace(write=write))


def test_gate_runs_ready_apps_and_skips_drafting(tmp_path, monkeypatch, capsys, example_ledger):
    monkeypatch.setattr(apps, "APPLICATIONS", tmp_path)
    for name, status in (("2026-10-05-acme-ops", "ready"), ("2026-10-05-wip-ops", "drafting")):
        d = tmp_path / name
        d.mkdir()
        (d / "selection.yaml").write_text(yaml.safe_dump(CLEAN))
        (d / "meta.yaml").write_text(yaml.safe_dump({"status": status}))
    ready = apps.App(tmp_path / "2026-10-05-acme-ops")
    cli.run_fit(ready, solve=True)
    assert _gate(write=True) == 0
    report = json.loads((ready.dir / "report.json").read_text())
    assert set(report) == {"fit", "ats", "truth"}
    capsys.readouterr()
    rc = _gate()
    out = capsys.readouterr().out
    assert rc == 0, out
    assert "[drafting]" in out and not (tmp_path / "2026-10-05-wip-ops" / "report.json").exists()


def test_gate_is_read_only_and_fails_on_stale_artifacts(tmp_path, monkeypatch, capsys, example_ledger):
    """Checking must never rewrite a tracked file (another session's app), and a
    committed PDF or report that no longer matches the ledger is a failure."""
    monkeypatch.setattr(apps, "APPLICATIONS", tmp_path)
    d = tmp_path / "2026-10-05-acme-ops"
    d.mkdir()
    (d / "selection.yaml").write_text(yaml.safe_dump(CLEAN))
    (d / "meta.yaml").write_text(yaml.safe_dump({"status": "ready", "company": "Acme"}))
    a = apps.App(d)
    cli.run_fit(a, solve=True)
    assert _gate(write=True) == 0
    tracked = {p.name: p.read_bytes() for p in d.iterdir()}

    # A layout change (what a ledger edit to a used variant does) makes both
    # the fit report and the PDF stale; the plain gate reports and leaves them.
    layout = yaml.safe_load((d / "layout.yaml").read_text())
    layout["margin_x"] = round(layout["margin_x"] + 0.05, 2)
    a.write_layout(layout)
    tracked["layout.yaml"] = (d / "layout.yaml").read_bytes()
    capsys.readouterr()
    assert _gate() == 1
    out = capsys.readouterr().out
    assert "STALE report.json[fit]" in out and "rc gate --write" in out
    assert {p.name: p.read_bytes() for p in d.iterdir()} == tracked

    # A missing PDF is stale too.
    a.pdf.unlink()
    capsys.readouterr()
    assert _gate() == 1
    assert f"STALE {a.pdf.name} (missing)" in capsys.readouterr().out

    # --write regenerates; the plain gate is green again.
    assert _gate(write=True) == 0
    assert _gate() == 0


def test_gate_fails_ready_app_with_blocked_variant(tmp_path, monkeypatch, example_ledger):
    monkeypatch.setattr(apps, "APPLICATIONS", tmp_path)
    bad = copy.deepcopy(CLEAN)
    bad["sections"][1]["entries"][0]["roles"][1]["bullets"][0] = "inventory-forecast/stockouts-30"
    d = tmp_path / "2026-10-05-bad-ops"
    d.mkdir()
    (d / "selection.yaml").write_text(yaml.safe_dump(bad))
    (d / "meta.yaml").write_text(yaml.safe_dump({"status": "ready"}))
    assert _gate() == 1


@pytest.mark.parametrize("phrase,text,hit", [
    ("ERP", "interpreted the data", False),        # regression: substring hit
    ("AI", "built an ai forecast", True),
    ("AI", "maintain the build", False),
    ("AI", "first aid kit", False),                # acronyms take no suffix
    ("AI", "ai-powered tools", True),
    ("AI system", "two ai systems", True),
    ("launch", "tested and launched it", True),    # inflection still matches
    ("data", "a database", False),
    ("end-to-end", "ran it end-to-end.", True),
    ("cross-functional team", "led a cross-functional team of 6", True),
    ("Excel (pivot tables)", "excel (pivot tables) and", True),
])
def test_keyword_pattern(phrase, text, hit):
    assert bool(ats.keyword_pattern(phrase).search(ats.norm(text).lower())) is hit
