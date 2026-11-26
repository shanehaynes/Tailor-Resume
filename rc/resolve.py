"""Resolve an application's selection.yaml (ledger ids) into literal text for the template.

Every rendered string comes from the ledger: variant text, fact display/claim,
inventory items, or entity fields. The selection contributes only structure,
separators, and line labels. Truth and acknowledgment are checked by `rc truth`,
not here: resolution must also work for fixtures holding retired wording.
See docs/decisions/2026-10-04-resolved-selection.md.
"""
from pathlib import Path

import yaml

from rc import ledger
from rc.ledger import LedgerError

CONTACT_FORMAT = {
    "phone": ("Tel: {v}", None),
    "email": ("Email: {v}", "mailto:{v}"),
    "github": ("GitHub", "{v}"),
    "linkedin": ("LinkedIn", "{v}"),
    "blog": ("Blog", "{v}"),
    "website": ("Website", "{v}"),
    "location": ("{v}", None),
}


def _by_id(items, key, where):
    for it in items:
        if it["id"] == key:
            return it
    raise LedgerError(f"{where}: no {key!r}")


def _fact_text(f: dict) -> str:
    return f.get("display", f["claim"])


def _contact(data, keys):
    c = data["contact"]
    items = []
    for k in keys:
        label, url = CONTACT_FORMAT[k]
        v = c[k]
        text = label.format(v=v)
        item = {"text": text}
        if url:
            item["links"] = [{"text": v if "{v}" in label else text, "url": url.format(v=v)}]
        items.append(item)
    return {"name": c["name"], "items": items}


def _bullet(data, spec) -> dict:
    """spec: 'acc/variant' or {ref, link: true}. link=true links the project name prefix."""
    ref = spec if isinstance(spec, str) else spec["ref"]
    acc, var = ledger.find_variant(data, ref)
    out = {"id": ref, "text": var["text"]}
    if isinstance(spec, dict) and spec.get("link"):
        url, name = acc.node.get("url"), acc.node.get("name")
        if not url or not name or not var["text"].startswith(name):
            raise LedgerError(f"{ref}: link needs a ledger url and text starting with the name")
        out["links"] = [{"text": name, "url": url}]
    return out


def _fact_line(facts_by_id, spec, owner) -> dict:
    ids = spec["facts"]
    texts = []
    for fid in ids:
        if fid not in facts_by_id:
            raise LedgerError(f"{owner}: no fact {fid!r}")
        texts.append(_fact_text(facts_by_id[fid]))
    return {"id": f"{owner}:{'+'.join(ids)}", "text": spec.get("sep", "; ").join(texts)}


def _education(data, spec) -> dict:
    edu = _by_id(data["education"], spec["education"], "education")
    facts = {f["id"]: f for f in edu["facts"]}
    role = {"title": edu["degree"], "dates": str(edu["end"])}
    if dv := spec.get("degree_variant"):
        text = _by_id(edu.get("degree_variants", []), dv, f"{edu['id']}.degree_variants")["text"]
        parts = [p.strip() for p in text.split("|")]
        role["detail"] = parts[0] if len(parts) == 1 else parts
    bullets = [_fact_line(facts, line, edu["id"]) for line in spec.get("lines", [])]
    bullets += [_bullet(data, b) for b in spec.get("bullets", [])]
    role["bullets"] = bullets
    return {"org": edu["school"], "ref": edu["id"], "location": edu["location"], "roles": [role]}


def _employer(data, spec) -> dict:
    emp = _by_id(data["experience"], spec["employer"], "experience")
    roles = []
    for r in spec["roles"]:
        role = _by_id(emp["roles"], r["role"], emp["id"])
        roles.append({"title": role["title"], "dates": role["dates"],
                      "bullets": [_bullet(data, b) for b in r.get("bullets", [])]})
    out = {"org": emp["company"], "ref": emp["id"], "location": emp["location"], "roles": roles}
    if spec.get("descriptor", True) and emp.get("descriptor"):
        out["descriptor"] = emp["descriptor"]
    return out


def _skills(data, groups) -> str:
    inventory = {s for items in data["additional"]["skills"].values() for s in items}
    parts = []
    for g in groups:
        items = g if isinstance(g, list) else g["items"]
        for it in items:
            if it not in inventory:
                raise LedgerError(f"skills: {it!r} not in the ledger inventory")
        joined = ", ".join(items)
        parts.append(joined if isinstance(g, list) else f"{g['label']} ({joined})")
    return "; ".join(parts)


def _additional_line(data, spec) -> dict:
    add = data["additional"]
    line = {"id": f"additional:{spec['label']}", "label": spec["label"]}
    if "facts" in spec:
        facts = {f["id"]: f for f in ledger.additional_facts(data)}
        line["text"] = _fact_line(facts, {**spec, "sep": spec.get("sep", ", ")}, "additional")["text"]
    elif "skills" in spec:
        line["text"] = _skills(data, spec["skills"])
    elif "interests" in spec:
        projects = {p["id"]: p for p in data["projects"]}
        texts, links = [], []
        for it in spec["interests"]:
            if it in add.get("interests", []):
                texts.append(it)
            elif it.startswith("project:") and it[8:] in projects:
                p = projects[it[8:]]
                texts.append(p["name"])
                if p.get("url"):
                    links.append({"text": p["name"], "url": p["url"]})
            else:
                raise LedgerError(f"interests: {it!r} not in the ledger")
        line["text"] = ", ".join(texts)
        if links:
            line["links"] = links
    else:
        raise LedgerError(f"additional line {spec['label']!r}: needs facts, skills, or interests")
    return line


def resolve(selection: dict, data: dict, layout: dict | None = None) -> dict:
    """layout: solver-owned levers (the application's layout.yaml); content never lives there."""
    sections = []
    for s in selection["sections"]:
        out = {"heading": s["heading"]}
        entries = []
        for e in s.get("entries", []):
            entries.append(_education(data, e) if "education" in e else _employer(data, e))
        if entries:
            out["entries"] = entries
        if "bullets" in s:
            out["bullets"] = [_bullet(data, b) for b in s["bullets"]]
        if "lines" in s:
            out["lines"] = [_additional_line(data, l) for l in s["lines"]]
        sections.append(out)
    return {"layout": layout if layout is not None else selection.get("layout", {}),
            "contact": _contact(data, selection.get(
                "contact", [k for k in ("phone", "email", "github", "linkedin") if k in data["contact"]])),
            "sections": sections}


def resolve_file(selection_path: Path, out_path: Path, ledger_path: Path = ledger.LEDGER) -> dict:
    resolved = resolve(yaml.safe_load(Path(selection_path).read_text()), ledger.load(ledger_path))
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(yaml.safe_dump(resolved, sort_keys=False, allow_unicode=True, width=1000))
    return resolved
