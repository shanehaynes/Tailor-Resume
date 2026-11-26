"""Examples in the skills must work against the example ledger, so a new owner's
AI copying them starts from something that resolves and passes `rc truth`."""
import re

import yaml

from rc import ledger, resolve, truth
from rc.paths import ROOT


def test_selection_format_example_resolves_and_passes_truth():
    doc = (ROOT / ".claude" / "skills" / "tailor-resume" / "selection.md").read_text()
    block = re.search(r"```yaml\n(.*?)```", doc, re.S)
    assert block, "selection.md has no yaml example"
    selection = yaml.safe_load(block.group(1))
    data = ledger.load(ROOT / "ledger" / "example.yaml")
    resolve.resolve(selection, data)
    result = truth.check(selection, data)
    assert result["ok"], result["failures"]
