import copy
import json
from pathlib import Path

import pytest

from rc import ledger
from rc.paths import LEDGER, ROOT, SCHEMA

FIXTURE = Path(__file__).parent / "fixtures" / "ledger-min.yaml"
EXAMPLE = ROOT / "ledger" / "example.yaml"


@pytest.fixture
def data():
    return ledger.load(FIXTURE)


def acc_and(data, vid):
    return ledger.find_variant(data, f"widget/{vid}")


def test_owner_ledger_is_valid():
    """ledger/ledger.yaml: the placeholder in a fresh copy, the owner's ledger after onboarding."""
    assert ledger.check(LEDGER) == []


def test_example_ledger_is_valid():
    assert ledger.check(EXAMPLE) == []


def test_example_exercises_every_status():
    data = ledger.load(EXAMPLE)
    facts = [f for a in ledger.accomplishments(data) for f in a.node["facts"]]
    facts += [f for e in data["education"] for f in e["facts"]] + ledger.additional_facts(data)
    assert {f["status"] for f in facts} == {"confirmed", "consistent", "single", "conflict", "derived", "retired"}
    variants = [v for a in ledger.accomplishments(data) for v in a.node["variants"]]
    assert {v["status"] for v in variants if "status" in v} == {"proposed", "single", "conflict", "retired"}
    degrees = [v for e in data["education"] for v in e.get("degree_variants", [])]
    assert {v["status"] for v in degrees} == {"confirmed", "proposed", "retired"}
    assert any("|" in v["text"] for v in degrees)
    assert any(a.node.get("groups") for a in ledger.accomplishments(data))
    assert data["open_questions"] and data["resolved_questions"]


def test_example_covers_every_category_and_field():
    """Onboarding copies the example's shape; every optional field needs a worked case."""
    data = ledger.load(EXAMPLE)
    assert all(data["additional"].get(k) for k in ledger.ADDITIONAL_FACTS)
    assert set(json.loads(SCHEMA.read_text())["properties"]["contact"]["properties"]) <= set(data["contact"])
    edu_keys = {k for e in data["education"] for k in e}
    assert {"major_official", "emphasis_official", "second_major_official", "status", "content"} <= edu_keys
    assert any("note" in r for e in data["experience"] for r in e["roles"])
    assert any("descriptor" not in e for e in data["experience"])
    assert any(p.get("url") is None and p.get("url_note") for p in data["projects"])
    assert "familiar_only" in data["additional"]["skills"]


def test_additional_categories_match_schema():
    props = json.loads(SCHEMA.read_text())["properties"]["additional"]["properties"]
    assert set(props) == set(ledger.ADDITIONAL_FACTS) | {"skills", "interests"}


def test_additional_fact_ids_unique_across_categories(data):
    d = copy.deepcopy(data)
    d["additional"]["awards"] = [{"id": "dup", "claim": "x", "status": "confirmed"}]
    d["additional"]["memberships"] = [{"id": "dup", "claim": "y", "status": "confirmed"}]
    assert any("additional: duplicate id 'dup'" in e for e in ledger.validate(d))


def test_fixture_is_valid(data):
    assert ledger.validate(data) == []


def test_duplicate_keys_rejected(tmp_path):
    p = tmp_path / "dup.yaml"
    p.write_text("a: {status: conflict, status: retired}\n")
    with pytest.raises(ledger.LedgerError, match="duplicate key 'status' at line 1"):
        ledger.load(p)


def test_dates_stay_strings(data):
    assert data["resolved_questions"][0]["resolved"] == "2026-10-04"


@pytest.mark.parametrize("text,want", [
    ("~$1.4M over 3 years", {"1.4M", "3"}),
    ("2,300+ SKUs and 45 contract carriers", {"2300", "45"}),
    ("+18% on-time pickup; 94% of loads", {"18", "94"}),
    ("12-week pilot under SOP 4.2", {"12", "4.2"}),
    ("over three years, from one warehouse", {"3"}),
    ("the one that fits, every one you remove", set()),
    ("Windows 11; a team of 4.", {"11", "4"}),
    ("no numbers here, someone", set()),
])
def test_numbers(text, want):
    assert ledger.numbers(text) == want


@pytest.mark.parametrize("vid,level,status", [
    ("clear", ledger.CLEAR, "confirmed"),
    ("needs-ack", ledger.NEEDS_ACK, "single"),
    ("proposed", ledger.NEEDS_ACK, "proposed"),
    ("blocked", ledger.BLOCKED, "conflict"),
    ("retired", ledger.BLOCKED, "retired"),
])
def test_effective_status(data, vid, level, status):
    eff = ledger.effective_status(*acc_and(data, vid))
    assert (eff.level, eff.status) == (level, status)


def test_effective_status_names_reasons(data):
    eff = ledger.effective_status(*acc_and(data, "needs-ack"))
    assert eff.reasons == ["fact savings: single"]


def test_find_variant_errors(data):
    with pytest.raises(ledger.LedgerError, match="no variant"):
        ledger.find_variant(data, "widget/nope")
    with pytest.raises(ledger.LedgerError, match="no accomplishment"):
        ledger.find_variant(data, "nope/clear")


def _widget(d):
    return d["experience"][0]["roles"][0]["accomplishments"][0]


def test_unknown_fact_in_uses(data):
    _widget(data)["variants"][0]["uses"].append("ghost")
    assert any("uses unknown fact 'ghost'" in e for e in ledger.validate(data))


def test_untraced_number(data):
    _widget(data)["variants"][0]["text"] += "; 99% faster"
    assert any("numbers ['99'] not in used facts" in e for e in ledger.validate(data))


def test_retired_variants_skip_number_trace(data):
    assert not any("widget/retired" in e for e in ledger.validate(data))


def test_duplicate_ids(data):
    d = copy.deepcopy(data)
    _widget(d)["facts"].append({"id": "crew-6", "claim": "x", "status": "single"})
    d["projects"].append({"id": "acme-dev", "name": "Clash", "facts": [], "variants": []})
    errs = ledger.validate(d)
    assert any("widget.facts: duplicate id 'crew-6'" in e for e in errs)
    assert any("ledger: duplicate id 'acme-dev'" in e for e in errs)


def test_unknown_group_member(data):
    _widget(data)["groups"][0]["variants"].append("ghost")
    assert any("unknown variant 'ghost'" in e for e in ledger.validate(data))


def test_schema_rejects_bad_status(data):
    _widget(data)["facts"][0]["status"] = "probably"
    assert any(e.startswith("schema:") for e in ledger.validate(data))


def test_derived_requires_derivation(data):
    _widget(data)["facts"][0]["status"] = "derived"
    assert any("derivation" in e for e in ledger.validate(data))
