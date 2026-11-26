import datetime as dt

import pytest
import yaml

from rc import app as apps
from rc import ledger, newapp, status
from rc.paths import ROOT


def test_new_app_from_text(tmp_path):
    d = newapp.new_app("Acme Corp", "Operations Analyst, Summer Intern", url="https://x.test/job",
                       text="Do operations things.\n", date=dt.date(2026, 10, 5), root=tmp_path)
    assert d.name == "2026-10-05-acme-corp-operations-analyst-summer-intern"
    assert (d / "posting.md").read_text().endswith("Do operations things.\n")
    meta = yaml.safe_load((d / "meta.yaml").read_text())
    assert meta["status"] == "drafting" and meta["url"] == "https://x.test/job"
    with pytest.raises(FileExistsError):
        newapp.new_app("Acme Corp", "Operations Analyst, Summer Intern", text="x", date=dt.date(2026, 10, 5), root=tmp_path)


def test_fetch_failure_asks_for_paste(monkeypatch):
    class R:
        headers = type("H", (), {"get_content_charset": lambda self: "utf-8"})()
        def read(self): return b"<html><script>app()</script><div id=root></div></html>"
        def __enter__(self): return self
        def __exit__(self, *a): pass
    monkeypatch.setattr(newapp.urllib.request, "urlopen", lambda *a, **k: R())
    with pytest.raises(newapp.FetchFailed, match="JS-rendered"):
        newapp.fetch("https://x.test/job")


def test_html_to_text_keeps_structure():
    p = newapp._Text()
    p.feed("<h2>About</h2><p>We build.</p><ul><li>SQL</li><li>Python</li></ul><script>SECRET()</script>")
    text = "".join(p.out)
    assert "- SQL" in text and "- Python" in text and "We build." in text
    assert "SECRET" not in text


def test_status_reports_ledger_health(monkeypatch, tmp_path):
    monkeypatch.setattr(apps, "APPLICATIONS", tmp_path)
    monkeypatch.setattr(ledger.load, "__defaults__", (ROOT / "ledger" / "example.yaml",))
    out = status.report()
    assert "none yet" in out and "open questions: 2" in out
    assert "carrier-scorecard/base" in out.split("variants conflict:")[1].splitlines()[0]
    assert "dock-scheduling/detention" in out
