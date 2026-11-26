"""Phase 6: cover-letter parsing, truth checks, one-page render."""
from pathlib import Path

import pytest

from rc import cover, ledger
from rc.paths import ROOT

WORK = ROOT / "build" / "test-cover"
EXAMPLE = ROOT / "ledger" / "example.yaml"


def letter(tmp_path, body, front="date: October 5, 2026\nrecipient: [Hiring Team]\n"):
    p = tmp_path / "cover-letter.md"
    p.write_text(f"---\n{front}---\n{body}")
    return cover.parse(p)


@pytest.fixture(scope="module")
def data():
    return ledger.load(EXAMPLE)


def test_parse_attaches_citations_to_paragraphs(tmp_path):
    L = letter(tmp_path, """Dear Team,

I shipped it. <!-- ledger: route-ledger.what, route-ledger.stack -->
<!-- source: https://x.test/a | "We serve 5 regions." -->

<!-- research note; source: https://x.test/b | "Founded in 1983." -->
""")
    assert [p.text for p in L.paras] == ["Dear Team,", "I shipped it."]
    assert L.paras[1].facts == ["route-ledger.what", "route-ledger.stack"]
    assert L.paras[1].sources == [("https://x.test/a", "We serve 5 regions.")]


def test_traced_numbers_pass(tmp_path, data):
    L = letter(tmp_path, "Empty miles fell 18% across 140 routes. "
                         "<!-- ledger: route-optimization.miles-cut, route-optimization.routes -->")
    assert cover.check(L, data)["ok"]


def test_untraced_number_fails(tmp_path, data):
    L = letter(tmp_path, "Empty miles fell 25%. <!-- ledger: route-optimization.miles-cut -->")
    assert any("numbers ['25']" in f for f in cover.check(L, data)["failures"])


def test_company_numbers_trace_to_source_quotes(tmp_path, data):
    ok = letter(tmp_path, 'Acme Corp has 100 million customers. <!-- source: https://x.test | "100 million customers" -->')
    assert cover.check(ok, data)["ok"]
    bad = letter(tmp_path, "Acme Corp has 100 million customers. <!-- source: https://x.test -->")
    assert any("no verbatim quote" in f for f in cover.check(bad, data)["failures"])


@pytest.mark.parametrize("ref,match", [
    ("route-optimization.ghost", "unknown ledger fact"),
    ("cross-dock.misroutes-pct", "is retired"),
    ("dock-scheduling.detention", "is single"),
    ("additional.forklift", "is retired"),
])
def test_bad_fact_refs(tmp_path, data, ref, match):
    L = letter(tmp_path, f"A claim. <!-- ledger: {ref} -->")
    assert any(match in f for f in cover.check(L, data)["failures"])


def test_single_fact_passes_with_ack(tmp_path, data):
    L = letter(tmp_path, "A claim. <!-- ledger: dock-scheduling.detention -->",
               front="acknowledge: {dock-scheduling.detention: 'owner 2026-10-05: yes'}\n")
    assert cover.check(L, data)["ok"]


def test_additional_facts_are_citable(tmp_path, data):
    L = letter(tmp_path, "Won an award in 2024. <!-- ledger: additional.ops-award, additional.food-bank -->")
    assert cover.check(L, data)["ok"]


def test_long_uncited_paragraph_warns(tmp_path, data):
    L = letter(tmp_path, " ".join(["word"] * 30))
    r = cover.check(L, data)
    assert r["ok"] and "no ledger or source citation" in r["warnings"][0]


def test_render_one_page_and_overflow(tmp_path, data):
    short = letter(tmp_path, "Dear Team,\n\nOne paragraph.\n\nSincerely,\nJamie Rivera")
    assert cover.render(short, data, WORK, WORK / "short.pdf") == 1
    long = letter(tmp_path, "\n\n".join(["Sentence of filler text for length. " * 12] * 12))
    assert cover.render(long, data, WORK, WORK / "long.pdf") == 2
