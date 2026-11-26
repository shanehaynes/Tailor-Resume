"""`rc status`: applications by status, and ledger health."""
from collections import defaultdict

from rc import app as apps
from rc import ledger, truth


def report() -> str:
    data = ledger.load()
    out = ["APPLICATIONS"]
    groups = defaultdict(list)
    for a in apps.all_apps():
        groups[a.status].append(a)
    for st in apps.STATES:
        for a in groups.get(st, []):
            m = a.meta
            line = f"  {st:9} {a.slug}"
            if m.get("deadline"):
                line += f"  (deadline {m['deadline']})"
            out.append(line)
            if st == "submitted":
                for f in truth.check(a.selection, data)["failures"]:
                    out.append(f"            ledger drift: {f}")
    if len(out) == 1:
        out.append("  none yet")

    out.append("LEDGER")
    counts = defaultdict(list)
    for acc in ledger.accomplishments(data):
        for f in acc.node["facts"]:
            if f["status"] in ("single", "conflict"):
                counts[f"facts {f['status']}"].append(f"{acc.id}.{f['id']}")
        for v in acc.node["variants"]:
            eff = ledger.effective_status(acc, v)
            if v.get("status") == "conflict" or (eff.status == "conflict" and v.get("status") != "retired"):
                counts["variants conflict"].append(f"{acc.id}/{v['id']}")
            elif eff.level == ledger.NEEDS_ACK:
                counts[f"variants needing ack ({eff.status})"].append(f"{acc.id}/{v['id']}")
    for k in sorted(counts):
        out.append(f"  {k}: {len(counts[k])}  " + ", ".join(counts[k]))
    out.append(f"  open questions: {len(data['open_questions'])}")
    out += [f"    {q['id']}" for q in data["open_questions"]]
    return "\n".join(out)
