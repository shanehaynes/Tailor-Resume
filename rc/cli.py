"""`rc` entrypoint. See docs/spec.md §6."""
import argparse
import json
import sys
from pathlib import Path

import pdfplumber

from rc import app as apps
from rc import ats, cover, fit, ledger, newapp, status, truth
from rc.paths import LEDGER, ROOT


def _say(ok: bool, name: str, lines: list[str]) -> int:
    for l in lines:
        print(f"  {l}")
    print(f"{name}: {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


def cmd_ledger_check(args) -> int:
    errors = ledger.check(Path(args.path))
    for e in errors:
        print(e, file=sys.stderr)
    if errors:
        print(f"ledger: {len(errors)} error(s)", file=sys.stderr)
        return 1
    print(f"ledger ok: {args.path}")
    return 0


def _out(a: apps.App, write: bool, name: str) -> Path:
    """Tracked path when writing; a scratch copy under build/ when only checking."""
    if write:
        return a.dir / name
    a.scratch.mkdir(parents=True, exist_ok=True)
    return a.scratch / name


def run_fit(a: apps.App, solve: bool = False, write: bool = True) -> dict:
    data = ledger.load()
    constraints = a.selection.get("constraints")
    if solve:
        s = fit.solve(a.resolved(data), a.work / "solve", constraints)
        print(f"solver: {s.note} ({s.trials} renders)")
        if s.ok:
            old = a.layout
            a.write_layout(s.layout)
            changed = {k: (old.get(k), v) for k, v in s.layout.items() if old.get(k) != v}
            for k, (o, n) in sorted(changed.items()):
                print(f"  layout.yaml {k}: {o} -> {n}")
    m = a.build(data, _out(a, write, a.pdf.name))
    fails = fit.check(m, constraints)
    print(fit.table(m, fails))
    report = fit.to_report(m, fails)
    if write:
        a.update_report("fit", report)
    return report


def run_ats(a: apps.App, write: bool = True) -> dict:
    pdf = _out(a, write, a.pdf.name)
    a.build(out=pdf)
    r = ats.check(pdf, a.resolved(), a.dir / "analysis.md")
    lines = r["failures"] + [f"keyword {k['status']:12} {k['phrase']!r}" for k in r["keywords"]]
    _say(r["ok"], "ats", lines)
    if write:
        a.update_report("ats", r)
    return r


def run_truth(a: apps.App, write: bool = True) -> dict:
    r = truth.check(a.selection, ledger.load())
    lines = ([f"FAIL {f}" for f in r["failures"]] + [f"warn {w}" for w in r["warnings"]]
             + [f"ack  {x['ref']}: {x['note']}" for x in r["acknowledged"]])
    _say(r["ok"], "truth", lines)
    if write:
        a.update_report("truth", r)
    return r


def run_cover(a: apps.App, write: bool = True) -> dict:
    data = ledger.load()
    letter = cover.parse(a.dir / "cover-letter.md")
    r = cover.check(letter, data)
    pages = cover.render(letter, data, a.work, _out(a, write, "cover-letter.pdf"))
    if pages != 1:
        r["ok"] = False
        r["failures"].append(f"cover letter runs {pages} pages; must be one")
    r["pages"] = pages
    lines = [f"FAIL {f}" for f in r["failures"]] + [f"warn {w}" for w in r["warnings"]]
    _say(r["ok"], f"cover ({r['words']} words, {pages} page)", lines)
    if write:
        a.update_report("cover", r)
    return r


def _pdf_text(p: Path) -> str:
    with pdfplumber.open(p) as pdf:
        return "\n".join(page.extract_text() or "" for page in pdf.pages)


def drift(a: apps.App, results: dict[str, dict]) -> list[str]:
    """Committed artifacts that no longer match what the ledger and selection
    produce. Text, not bytes, for PDFs: layout drift already shows in the fit
    report, and text survives platform differences in PDF metadata."""
    out = []
    committed = a.report
    for key, r in results.items():
        if committed.get(key) != json.loads(json.dumps(r, sort_keys=True)):
            out.append(f"report.json[{key}]")
    pdfs = [a.pdf.name] + (["cover-letter.pdf"] if "cover" in results else [])
    for name in pdfs:
        tracked, fresh = a.dir / name, a.scratch / name
        if not tracked.exists():
            out.append(f"{name} (missing)")
        elif tracked.read_bytes() != fresh.read_bytes() and _pdf_text(tracked) != _pdf_text(fresh):
            out.append(name)
    return out


def _warn_if_not_set_up() -> None:
    """A warning, not a failure: the placeholder ledger is valid, so nothing else stops
    a resume headed "Your Name" from being built before onboarding."""
    try:
        placeholder = ledger.load()["contact"]["name"] == "Your Name"
    except (ledger.LedgerError, KeyError, OSError):
        placeholder = False
    if placeholder or not (ROOT / "profile" / "preferences.md").exists():
        print("warning: this copy is not set up yet: run /onboard in Claude Code.", file=sys.stderr)


def cmd_cover(args) -> int:
    _warn_if_not_set_up()
    return 0 if run_cover(apps.find(args.app))["ok"] else 1


def cmd_fit(args) -> int:
    _warn_if_not_set_up()
    r = run_fit(apps.find(args.app), args.solve)
    return _say(r["ok"], "fit", [])


def cmd_ats(args) -> int:
    return 0 if run_ats(apps.find(args.app))["ok"] else 1


def cmd_truth(args) -> int:
    return 0 if run_truth(apps.find(args.app))["ok"] else 1


def cmd_gate(args) -> int:
    """`ready` apps must pass fit, ats, truth, and their committed PDFs and
    report.json must match what the current ledger produces. `submitted` apps are
    frozen: truth problems from later ledger changes are warnings only. Others
    are skipped.

    Read-only by default: renders go to build/, so checking one application never
    dirties another session's files. `--write` regenerates them in place."""
    write = bool(getattr(args, "write", False))
    bad = stale = 0
    for a in apps.all_apps():
        st = a.status
        print(f"== {a.slug} [{st}]")
        if st == "ready":
            results = {"fit": run_fit(a, write=write), "ats": run_ats(a, write=write),
                       "truth": run_truth(a, write=write)}
            if (a.dir / "cover-letter.md").exists():
                results["cover"] = run_cover(a, write=write)
            bad += sum(not r["ok"] for r in results.values())
            if not write:
                for d in drift(a, results):
                    print(f"  STALE {d}: committed copy differs from what the ledger now produces")
                    stale += 1
        elif st == "submitted":
            r = truth.check(a.selection, ledger.load())
            for f in r["failures"]:
                print(f"  warn (submitted, frozen): {f}")
    if stale:
        print(f"  {stale} stale artifact(s): run `uv run rc gate --write` in your worktree, review the diff, commit.")
    print(f"gate: {'FAIL' if bad or stale else 'PASS'}")
    return 1 if bad or stale else 0


def cmd_new_app(args) -> int:
    _warn_if_not_set_up()
    text =Path(args.file).read_text() if args.file else None
    try:
        d = newapp.new_app(args.company, args.role, url=args.url, text=text)
    except newapp.FetchFailed as e:
        print(f"new-app: {e}. Paste the posting text into a file and rerun with --file.", file=sys.stderr)
        return 2
    print(d)
    return 0


def cmd_status(args) -> int:
    print(status.report())
    return 0


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="rc")
    sub = p.add_subparsers(dest="cmd", required=True)
    lp = sub.add_parser("ledger", help="ledger operations").add_subparsers(dest="sub", required=True)
    c = lp.add_parser("check", help="validate schema, ids, uses, and number traces")
    c.add_argument("path", nargs="?", default=str(LEDGER))
    c.set_defaults(func=cmd_ledger_check)
    f = sub.add_parser("fit", help="render, measure, check layout constraints")
    f.add_argument("app")
    f.add_argument("--solve", action="store_true", help="move layout levers (spacing, margins, font) to pass")
    f.set_defaults(func=cmd_fit)
    for name, fn, hlp in (("ats", cmd_ats, "ATS round-trip and keyword coverage"),
                          ("truth", cmd_truth, "statuses, acknowledgments, number traces"),
                          ("cover", cmd_cover, "check and render cover-letter.md")):
        s = sub.add_parser(name, help=hlp)
        s.add_argument("app")
        s.set_defaults(func=fn)
    n = sub.add_parser("new-app", help="scaffold an application folder and save the posting")
    n.add_argument("--company", required=True)
    n.add_argument("--role", required=True)
    n.add_argument("--url")
    n.add_argument("--file", help="posting text (when the URL can't be fetched)")
    n.set_defaults(func=cmd_new_app)
    sub.add_parser("status", help="applications by status; ledger health").set_defaults(func=cmd_status)
    g = sub.add_parser("gate", help="fit+ats+truth on every ready application; fails on stale artifacts")
    g.add_argument("--write", action="store_true", help="regenerate PDFs and report.json in place")
    g.set_defaults(func=cmd_gate)
    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
