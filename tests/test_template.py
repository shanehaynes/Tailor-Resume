"""Phase 3: template renders the golden resume; resolver builds it from ledger ids."""
import copy
import re
import subprocess
from pathlib import Path

import pytest
import yaml

from rc import ledger, resolve
from rc.paths import ROOT
from rc.render import render

GOLDEN = ROOT / "tests" / "golden" / "base.resolved.yaml"
GOLDEN_TEXT = ROOT / "tests" / "golden" / "base.txt"
EXAMPLE = ROOT / "ledger" / "example.yaml"
FIXTURES = Path(__file__).parent / "fixtures"


def text(pdf: Path) -> str:
    raw = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    return " ".join(raw.split())


@pytest.fixture(scope="module")
def golden_pdf(tmp_path_factory):
    return render(GOLDEN, tmp_path_factory.mktemp("golden") / "base.pdf")


@pytest.fixture(scope="module")
def data():
    return ledger.load(EXAMPLE)


def test_golden_text_is_stable(golden_pdf):
    """Recorded once (tests/golden/base.txt); the text layer must match on every machine and in CI."""
    assert text(golden_pdf) == GOLDEN_TEXT.read_text().strip()


def test_golden_is_one_page_carlito_only(golden_pdf):
    info = subprocess.run(["pdfinfo", str(golden_pdf)], capture_output=True, text=True, check=True).stdout
    assert re.search(r"^Pages:\s+1$", info, re.M), info
    fonts = subprocess.run(["pdffonts", str(golden_pdf)], capture_output=True, text=True, check=True).stdout
    names = [l.split()[0] for l in fonts.splitlines()[2:]]
    assert names and all("Carlito" in n for n in names), names


def test_hyphenated_words_never_split(golden_pdf):
    raw = subprocess.run(["pdftotext", "-raw", str(golden_pdf), "-"], capture_output=True, text=True, check=True).stdout
    assert not any(line.rstrip().endswith("-") for line in raw.splitlines())


def _strings(node):
    """All rendered text in a resolved tree, in order (ids, refs, layout, urls excluded)."""
    if isinstance(node, dict):
        for k in sorted(node):
            if k not in ("id", "ref", "layout", "links"):
                yield from _strings(node[k])
    elif isinstance(node, list):
        for v in node:
            yield from _strings(v)
    elif node is not None:
        yield str(node)


def test_example_selection_resolves_to_golden_text(data):
    sel = yaml.safe_load((FIXTURES / "example.selection.yaml").read_text())
    got = resolve.resolve(sel, data)
    assert list(_strings(got)) == list(_strings(yaml.safe_load(GOLDEN.read_text())))


def test_two_line_degree_variant_splits(data):
    sel = {"sections": [{"heading": "Education",
                         "entries": [{"education": "edu-brookfield", "degree_variant": "official-two-line"}]}]}
    role = resolve.resolve(sel, data)["sections"][0]["entries"][0]["roles"][0]
    assert role["detail"] == ["Supply Chain Management, Transportation and Logistics", "Economics Minor"]


def test_two_line_degree_renders_each_line(tmp_path):
    g = yaml.safe_load(GOLDEN.read_text())
    g["sections"][0]["entries"][1]["roles"][0]["detail"] = ["First major line", "Second major line"]
    src = ROOT / "build" / "test-two-line.resolved.yaml"
    src.parent.mkdir(exist_ok=True)
    src.write_text(yaml.safe_dump(g))
    raw = subprocess.run(["pdftotext", "-raw", str(render(src, tmp_path / "t.pdf")), "-"],
                         capture_output=True, text=True, check=True).stdout.splitlines()
    i = raw.index("Bachelor of Science 2021")
    assert raw[i + 1:i + 3] == ["First major line", "Second major line"]


@pytest.mark.parametrize("sel,match", [
    ({"sections": [{"heading": "P", "bullets": ["route-ledger/nope"]}]}, "no variant"),
    ({"sections": [{"heading": "A", "lines": [{"label": "S", "skills": [["COBOL"]]}]}]}, "not in the ledger inventory"),
    ({"sections": [{"heading": "A", "lines": [{"label": "I", "interests": ["golf"]}]}]}, "not in the ledger"),
    ({"sections": [{"heading": "E", "entries": [{"education": "edu-northgate", "lines": [{"facts": ["ghost"]}]}]}]}, "no fact"),
    ({"sections": [{"heading": "P", "bullets": [{"ref": "carrier-rfp/base", "link": True}]}]}, "link needs a ledger url"),
    ({"sections": [{"heading": "A", "lines": [{"label": "X", "facts": ["forklift", "ghost"]}]}]}, "no fact"),
])
def test_resolver_rejects_text_not_in_ledger(data, sel, match):
    with pytest.raises(ledger.LedgerError, match=match):
        resolve.resolve(sel, data)


def test_project_link_uses_ledger_url(data):
    sel = {"sections": [{"heading": "P", "bullets": [{"ref": "route-ledger/header", "link": True}]}]}
    b = resolve.resolve(sel, data)["sections"][0]["bullets"][0]
    assert b["links"] == [{"text": "Route Ledger", "url": "https://example.org/route-ledger/"}]


def test_every_additional_category_resolves(data):
    """Each fact list named in ledger.ADDITIONAL_FACTS is selectable by id."""
    d = copy.deepcopy(data)
    for k in ledger.ADDITIONAL_FACTS:
        d["additional"][k] = [{"id": f"x-{k}", "claim": f"A {k} entry", "status": "confirmed"}]
    sel = {"sections": [{"heading": "A", "lines": [{"label": k, "facts": [f"x-{k}"]} for k in ledger.ADDITIONAL_FACTS]}]}
    lines = resolve.resolve(sel, d)["sections"][0]["lines"]
    assert [l["text"] for l in lines] == [f"A {k} entry" for k in ledger.ADDITIONAL_FACTS]


def test_optional_contact_fields(data):
    d = copy.deepcopy(data)
    d["contact"]["website"] = "https://example.org/portfolio/"
    c = resolve.resolve({"contact": ["phone", "location", "website"], "sections": []}, d)["contact"]
    assert [it["text"] for it in c["items"]] == ["Tel: (555) 010-0142", "Lakeshore City, ST", "Website"]
    assert "links" not in c["items"][1]
    assert c["items"][2]["links"] == [{"text": "Website", "url": "https://example.org/portfolio/"}]
