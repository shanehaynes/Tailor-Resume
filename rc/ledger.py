"""Load, validate, and query the career ledger (schema v1, ledger/schema.json)."""
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator

import jsonschema
import yaml

from rc.paths import LEDGER, SCHEMA


class LedgerError(Exception):
    pass


class _StrictLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate keys and keeps dates as strings."""

    def construct_mapping(self, node, deep=False):
        seen = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise LedgerError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


_StrictLoader.add_constructor(
    "tag:yaml.org,2002:timestamp", lambda loader, node: loader.construct_scalar(node))


def load(path: Path = LEDGER) -> dict:
    return yaml.load(Path(path).read_text(), Loader=_StrictLoader)


# --- numbers -----------------------------------------------------------------

# Spelled-out counts, two through twelve. "one" is excluded: it is far more often a
# pronoun ("the one I want") than a count, and a lone "1" is still traced.
_WORDS = {w: str(i) for i, w in enumerate(
    "zero one two three four five six seven eight nine ten eleven twelve".split()) if i >= 2}
_WORD_RE = re.compile(r"\b(" + "|".join(_WORDS) + r")\b", re.IGNORECASE)
_NUM_RE = re.compile(r"(?<![\w.])\d[\d,]*(?:\.\d+)?(?:[MKB](?![A-Za-z]))?")


def numbers(text: str) -> set[str]:
    """Numeric tokens, normalized: '~$1.4M' -> '1.4M', '2,300+' -> '2300', 'three' -> '3'."""
    text = _WORD_RE.sub(lambda m: _WORDS[m.group(1).lower()], text)
    return {tok.replace(",", "").rstrip(",") for tok in _NUM_RE.findall(text)}


# --- additional facts --------------------------------------------------------

# Fact lists under `additional:`, each optional. One place: validation, resolution,
# truth, and cover-letter citations all read this. Add a category here and in
# ledger/schema.json together (tests/test_ledger.py checks they agree).
ADDITIONAL_FACTS = ("lecturing", "certifications", "languages", "awards", "publications",
                    "volunteering", "memberships")


def additional_facts(data: dict) -> list[dict]:
    add = data["additional"]
    return [f for k in ADDITIONAL_FACTS for f in add.get(k, [])]


# --- traversal ---------------------------------------------------------------

@dataclass
class Accomplishment:
    id: str
    node: dict
    context: str  # e.g. "acme/acme-analyst", "edu-state", "projects"

    @property
    def facts(self) -> dict[str, dict]:
        return {f["id"]: f for f in self.node["facts"]}

    @property
    def variants(self) -> dict[str, dict]:
        return {v["id"]: v for v in self.node["variants"]}


def accomplishments(data: dict) -> Iterator[Accomplishment]:
    for edu in data["education"]:
        for acc in edu.get("accomplishments", []):
            yield Accomplishment(acc["id"], acc, edu["id"])
    for emp in data["experience"]:
        for role in emp["roles"]:
            for acc in role["accomplishments"]:
                yield Accomplishment(acc["id"], acc, f"{emp['id']}/{role['id']}")
    for proj in data["projects"]:
        yield Accomplishment(proj["id"], proj, "projects")


def find_variant(data: dict, ref: str) -> tuple[Accomplishment, dict]:
    """Resolve 'accomplishment-id/variant-id'."""
    acc_id, _, var_id = ref.partition("/")
    for acc in accomplishments(data):
        if acc.id == acc_id:
            if var_id in acc.variants:
                return acc, acc.variants[var_id]
            raise LedgerError(f"{ref}: no variant {var_id!r}")
    raise LedgerError(f"{ref}: no accomplishment {acc_id!r}")


# --- status ------------------------------------------------------------------

_RANK = {"confirmed": 0, "consistent": 0, "derived": 0,
         "single": 1, "proposed": 1, "conflict": 2, "retired": 3}
CLEAR, NEEDS_ACK, BLOCKED = "clear", "needs-ack", "blocked"


@dataclass
class Effective:
    level: str          # clear | needs-ack | blocked
    status: str         # worst underlying status
    reasons: list[str]  # e.g. ["variant: conflict", "fact requirements: single"]


def effective_status(acc: Accomplishment, variant: dict) -> Effective:
    """Worst of the variant's explicit status and its used facts' statuses."""
    pairs = []
    if "status" in variant:
        pairs.append((variant["status"], "variant"))
    facts = acc.facts
    pairs += [(facts[f]["status"], f"fact {f}") for f in variant["uses"] if f in facts]
    worst = max((s for s, _ in pairs), key=_RANK.__getitem__, default="consistent")
    rank = _RANK[worst]
    reasons = [f"{who}: {s}" for s, who in pairs if _RANK[s] > 0]
    level = CLEAR if rank == 0 else NEEDS_ACK if rank == 1 else BLOCKED
    return Effective(level, worst, reasons)


# --- validation --------------------------------------------------------------

def validate(data: dict) -> list[str]:
    schema = json.loads(SCHEMA.read_text())
    errors = [f"schema: /{'/'.join(map(str, e.absolute_path))}: {e.message}"
              for e in jsonschema.Draft202012Validator(schema).iter_errors(data)]
    if errors:
        return errors  # semantic checks assume a schema-valid shape

    def dupes(ids, where):
        seen = set()
        for i in ids:
            if i in seen:
                errors.append(f"{where}: duplicate id {i!r}")
            seen.add(i)

    global_ids = [q["id"] for q in data["open_questions"] + data["resolved_questions"]]
    global_ids += [e["id"] for e in data["education"]]
    for emp in data["experience"]:
        global_ids += [emp["id"]] + [r["id"] for r in emp["roles"]]
    global_ids += [a.id for a in accomplishments(data) if a.context != "projects"]
    global_ids += [p["id"] for p in data["projects"]]
    dupes(global_ids, "ledger")

    for edu in data["education"]:
        dupes([f["id"] for f in edu["facts"]], f"{edu['id']}.facts")
        dupes([v["id"] for v in edu.get("degree_variants", [])], f"{edu['id']}.degree_variants")
    dupes([f["id"] for f in additional_facts(data)], "additional")

    for acc in accomplishments(data):
        where = acc.id
        dupes([f["id"] for f in acc.node["facts"]], f"{where}.facts")
        dupes([v["id"] for v in acc.node["variants"]], f"{where}.variants")
        facts, variants = acc.facts, acc.variants
        for v in acc.node["variants"]:
            for f in v["uses"]:
                if f not in facts:
                    errors.append(f"{where}/{v['id']}: uses unknown fact {f!r}")
            if v.get("status") in ("retired", "conflict"):
                continue
            have = set().union(*(numbers(facts[f]["claim"]) for f in v["uses"] if f in facts))
            missing = numbers(v["text"]) - have
            if missing:
                errors.append(f"{where}/{v['id']}: numbers {sorted(missing)} not in used facts")
        for g in acc.node.get("groups", []):
            for vid in g["variants"]:
                if vid not in variants:
                    errors.append(f"{where}: group {g['id']!r} names unknown variant {vid!r}")
    return errors


def check(path: Path = LEDGER) -> list[str]:
    try:
        return validate(load(path))
    except (LedgerError, yaml.YAMLError) as e:
        return [f"load: {e}"]
