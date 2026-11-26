"""Truth check (spec §6; decisions truth-verbatim, variant-uses).

Bullets are ledger variants verbatim by construction (rc/resolve.py renders only
ledger text), so this checks what construction can't: statuses, acknowledgments,
and number traces. Every number in a selected variant must appear in the facts it
`uses`. Effective conflict or retired fails; single or proposed fails unless the
selection's `acknowledge:` names it with the owner's note.
"""
from rc import ledger, resolve
from rc.ledger import LedgerError


def _variant_refs(selection: dict) -> list[str]:
    refs = []
    for s in selection["sections"]:
        for e in s.get("entries", []):
            refs += e.get("bullets", [])
            for r in e.get("roles", []):
                refs += r.get("bullets", [])
        refs += s.get("bullets", [])
    return [r if isinstance(r, str) else r["ref"] for r in refs]


def _fact_refs(selection: dict, data: dict) -> list[tuple[str, dict]]:
    """(ack key, fact) for fact-built lines: education lines and additional facts."""
    out = []
    edus = {e["id"]: e for e in data["education"]}
    add = {f["id"]: f for f in ledger.additional_facts(data)}
    for s in selection["sections"]:
        for e in s.get("entries", []):
            if "education" in e:
                edu = edus[e["education"]]
                facts = {f["id"]: f for f in edu["facts"]}
                out += [(f"{edu['id']}/{fid}", facts[fid]) for l in e.get("lines", []) for fid in l["facts"]]
                if dv := e.get("degree_variant"):
                    v = next(v for v in edu["degree_variants"] if v["id"] == dv)
                    out.append((f"{edu['id']}/degree:{dv}", {"status": v["status"], "claim": v["text"]}))
        for l in s.get("lines", []):
            out += [(f"additional/{fid}", add[fid]) for fid in l.get("facts", [])]
    return out


def check(selection: dict, data: dict) -> dict:
    failures, warnings, acknowledged = [], [], []
    ack = selection.get("acknowledge") or {}
    used_acks = set()
    try:
        resolve.resolve(selection, data)  # every rendered string must come from the ledger
    except LedgerError as e:
        return {"ok": False, "failures": [f"resolve: {e}"], "warnings": [], "acknowledged": []}

    def gate(key: str, level: str, why: str):
        if level == ledger.BLOCKED:
            failures.append(f"{key}: {why} (blocked)")
        elif level == ledger.NEEDS_ACK:
            if ack.get(key):
                used_acks.add(key)
                acknowledged.append({"ref": key, "why": why, "note": ack[key]})
            else:
                failures.append(f"{key}: {why}; needs the owner's acknowledgment in selection.yaml `acknowledge:`")

    refs = _variant_refs(selection)
    for ref in refs:
        acc, var = ledger.find_variant(data, ref)
        eff = ledger.effective_status(acc, var)
        gate(ref, eff.level, ", ".join(eff.reasons))
        facts = acc.facts
        have = set().union(*(ledger.numbers(facts[f]["claim"]) for f in var["uses"] if f in facts))
        if missing := ledger.numbers(var["text"]) - have:
            failures.append(f"{ref}: numbers {sorted(missing)} not in the facts it uses")
        for g in acc.node.get("groups", []):
            if var["id"] in g["variants"]:
                absent = [v for v in g["variants"] if f"{acc.id}/{v}" not in refs]
                if absent:
                    warnings.append(f"{ref}: group {g['id']!r} selected without {absent}")
    for key, fact in _fact_refs(selection, data):
        st = fact["status"]
        level = (ledger.BLOCKED if st in ("conflict", "retired")
                 else ledger.NEEDS_ACK if st in ("single", "proposed") else ledger.CLEAR)
        gate(key, level, f"status {st}")
    for key in sorted(set(ack) - used_acks):
        warnings.append(f"acknowledge: {key!r} is not needed by anything selected (stale?)")
    return {"ok": not failures, "failures": failures, "warnings": warnings, "acknowledged": acknowledged}
