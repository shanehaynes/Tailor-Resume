"""An application folder (spec §5): applications/YYYY-MM-DD-company-role/.

Content lives in selection.yaml (ledger ids, written by Claude, decided by the owner).
Layout levers live in layout.yaml, written only by `rc fit --solve`, so the
solver never rewrites a file a person edits.
"""
import json
import re
from dataclasses import dataclass
from pathlib import Path

import yaml

from rc import fit, ledger, resolve
from rc.paths import ROOT

APPLICATIONS = ROOT / "applications"
STATES = ("drafting", "ready", "submitted", "archived")


@dataclass
class App:
    dir: Path

    @property
    def slug(self) -> str:
        return self.dir.name

    def _yaml(self, name: str, default=None):
        p = self.dir / name
        return yaml.safe_load(p.read_text()) if p.exists() else default

    @property
    def selection(self) -> dict:
        return self._yaml("selection.yaml")

    @property
    def meta(self) -> dict:
        return self._yaml("meta.yaml", {})

    @property
    def layout(self) -> dict:
        return self._yaml("layout.yaml", {})

    @property
    def status(self) -> str:
        s = self.meta.get("status", "drafting")
        if s not in STATES:
            raise ValueError(f"{self.slug}: meta.yaml status {s!r} not in {STATES}")
        return s

    @property
    def work(self) -> Path:
        return ROOT / "build" / "apps" / self.slug

    @property
    def pdf(self) -> Path:
        """resume-<company>.pdf: company from meta.yaml, lowercase alphanumerics only."""
        company = re.sub(r"[^a-z0-9]", "", str(self.meta.get("company", "")).lower())
        return self.dir / (f"resume-{company}.pdf" if company else "resume.pdf")

    def resolved(self, data: dict | None = None) -> dict:
        return resolve.resolve(self.selection, data or ledger.load(), self.layout)

    def build(self, data: dict | None = None, out: Path | None = None) -> fit.Measurement:
        """Resolve, render to out (default self.pdf), measure."""
        self.work.mkdir(parents=True, exist_ok=True)
        src = self.work / "resolved.yaml"
        src.write_text(yaml.safe_dump(self.resolved(data), sort_keys=False, allow_unicode=True, width=1000))
        return fit.measure(src, out or self.pdf)

    @property
    def scratch(self) -> Path:
        """Where the read-only gate renders, so checking never rewrites a tracked file."""
        return self.work / "gate"

    @property
    def report(self) -> dict:
        p = self.dir / "report.json"
        return json.loads(p.read_text()) if p.exists() else {}

    def write_layout(self, layout: dict) -> None:
        (self.dir / "layout.yaml").write_text(
            "# Written by `rc fit --solve`. Layout levers only; never edit content here.\n"
            + yaml.safe_dump(layout, sort_keys=True))

    def update_report(self, key: str, value: dict) -> None:
        p = self.dir / "report.json"
        report = json.loads(p.read_text()) if p.exists() else {}
        report[key] = value
        p.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n")


def find(name: str) -> App:
    p = Path(name)
    for cand in (p, APPLICATIONS / name):
        if (cand / "selection.yaml").exists():
            return App(cand.resolve())
    raise FileNotFoundError(f"no application with selection.yaml at {name!r}")


def all_apps() -> list[App]:
    return [App(p.parent) for p in sorted(APPLICATIONS.glob("*/selection.yaml"))]
