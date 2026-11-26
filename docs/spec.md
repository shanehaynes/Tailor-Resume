# Tailor-Resume Spec

Owner: whoever owns this copy (onboarded with `/onboard`). Quality over speed,
both for the system and its output. If something here is underspecified or
wrong, push back before building it.

## 1. What the system does

The core idea: **writing is judgment, layout is measurement.** An LLM can't see
where a line wraps, so every layout claim comes from rendering the PDF and
measuring it. Content comes from Claude working against a verified ledger, with
the owner deciding the positioning.

Pipeline for one application:
1. **Capture**: save the posting verbatim plus URL, date, and metadata.
2. **Analyze**: extract and rank requirements, keep the posting's exact phrases,
   map each to ledger accomplishments with a strength (strong / partial / gap).
3. **Angle**: propose 2–3 positioning angles (what leads, what's cut, the
   trade-off). **Stop and wait for the owner's choice.**
4. **Select & write**: choose accomplishments and variants. Adapt wording to the
   posting's language only where a ledger fact supports it.
5. **Fit loop**: render → measure → revise until every hard constraint passes.
6. **Verify**: ATS round-trip, truth check, and a fresh-context recruiter-skim review.
7. **Cover letter** (optional, separate pipeline).
8. **Record**: store the final PDF and report; mark `meta.yaml` submitted. Usage
   is derived from `applications/*/selection.yaml`, never written into the ledger
   (decision 2026-10-04-used-in-derived).

The owner's standing preferences (`profile/preferences.md`) and cover-letter
voice (`profile/voice.md`) shape steps 3, 4 and 7. They never override §2.

## 2. Invariants
See `CLAUDE.md`. The checks in §6 enforce them in code. The owner's copy holds
personal data, so its remote must be private (CLAUDE.md invariant 8).

## 3. Layout (hard constraints, all measured from the PDF)
- Exactly one page; usable height filled ≥ ~95% (configurable). Report as a number.
- Every bullet ≤ 2 lines.
- No orphans: a bullet's last line ≥ ~35% of line width (configurable).
- Lever order: (1) content: Claude, guided by the report; (2) spacing within
  bounds; (3) margins within bounds, floor 0.5in; (4) body font size, 10–11pt.
  A solver may move levers 2–4 automatically and must say when only content can fix it.
  The report gives actionable deltas, e.g. "`carrier-rfp/base`: 2 lines, last line
  12% full → cut ~8 chars or add ~40".
- Single column; headings EDUCATION, PROFESSIONAL EXPERIENCE, PROJECTS,
  ADDITIONAL INFORMATION; no text in images; ligatures and hyphenation off.
- Default look: `templates/resume.typ` (Carlito 10.5pt base, 0.6in side
  margins, small-caps headings with rules; decision 2026-10-04-template-fidelity).
  The golden fixture fills less than 95% of the page and would fail the fill
  constraint. That's expected: the golden test checks text and line counts, not
  the fill.

## 4. Cross-device determinism
- Typst pinned via `.typst-version` + `scripts/typst-checksums.txt`; `make setup`
  installs it into `bin/`. Bumping the version means re-recording all checksums,
  re-running golden tests, and writing a decision record.
- Fonts: Carlito in `fonts/`; every render uses `rc.paths.typst_compile_args`.
- Python via uv with a committed lockfile. CI runs the same `make check`.
- A determinism test: a golden fixture with recorded per-bullet line counts
  (`tests/golden/base.lines.json`) that must match on every machine and in CI.

## 5. Repo layout
```
CLAUDE.md  STATUS.md  README.md  CONTRIBUTING.md  Makefile  pyproject.toml  uv.lock  .typst-version
fonts/                       # committed, OFL
ledger/ledger.yaml           # the owner's source of truth (placeholder until onboarding)
ledger/example.yaml          # fictional, full-featured; tests and onboarding use it as the shape
ledger/schema.json
profile/                     # preferences.md, voice.md (written by onboarding) + *.example.md
templates/resume.typ         # renders entirely from a resolved YAML via yaml()
templates/cover-letter.typ
rc/                          # python package; `rc` CLI
  paths.py ledger.py resolve.py render.py fit.py ats.py truth.py cover.py
  app.py newapp.py status.py cli.py
tests/                       # unit tests, fixtures, golden renders (from ledger/example.yaml)
master/selection.yaml        # full-length master resume (created during onboarding)
applications/YYYY-MM-DD-company-role/
  posting.md analysis.md angle.md selection.yaml layout.yaml resume-<company>.pdf
  cover-letter.md cover-letter.pdf report.json meta.yaml
  # selection.yaml: content (ledger ids) + acknowledge + constraints.
  # layout.yaml: levers only, written by `rc fit --solve`, never by hand.
reference/                   # read-only historical inputs; the owner's earlier resumes in reference/resumes/
docs/spec.md  docs/decisions/
.claude/skills/  .claude/commands/
```

## 6. Components and acceptance criteria

**Ledger schema.** JSON Schema for `ledger.yaml`. Every fact, variant, status,
note, open question, and resolved question is preserved by any migration; show
the owner a migration as a diff and **wait for approval** before rewriting the
file. Statuses: confirmed, consistent, single, conflict, derived, proposed,
retired. Validation joins `make check`.
- Every fact and variant has an id, unique within its accomplishment; selections
  reference variants as `accomplishment/variant`.
- Every variant lists `uses:` the fact ids it relies on. Its **effective status**
  is the worst of its own explicit status and those facts' statuses
  (decision 2026-10-04-variant-uses).
- The loader rejects duplicate YAML keys (PyYAML silently keeps the last).
- `ledger/example.yaml` exercises every schema feature and passes the same check.

**Template.** Two stages: `rc` resolves `selection.yaml` (ledger ids) into
`build/resolved.yaml` (literal text plus ids); `resume.typ` reads only the
resolved file and knows nothing of the ledger schema. The golden fixture is a
resolved file built from `ledger/example.yaml` via
`tests/fixtures/example.selection.yaml` (decision
2026-10-04-resolved-selection). Layout parameters come from the selection.
Acceptance: the golden render's `pdftotext` text matches
`tests/golden/base.txt` modulo whitespace, and its per-bullet line counts match
`tests/golden/base.lines.json`. Degree rendering supports the official title on
two lines (ledger `degree_variants`).

**Fit checker: `rc fit <app>`.** Per-bullet table (id, lines, last-line fill %),
page count, page fill %, lever values. Non-zero exit on any hard-constraint
failure. Measured from the rendered PDF (pdfplumber character positions).
Bullet→id mapping via Typst metadata marks (decision 2026-10-05-fit-rules),
tested. Lever solver: spacing → margins → font, within bounds. Fixtures: a
known 3-line bullet, a known orphan, a page-2 overflow.

**ATS check: `rc ats <app>`.** `pdftotext` raw and layout modes. Fail on
ligature or replacement glyphs, interleaved reading order, or missing contact
info. Keyword coverage per exact phrase from `analysis.md`: present / ledger gap
(no supporting fact) / wording gap (fact exists, phrase unused).

**Truth check: `rc truth <app>`.** Every rendered line, not only bullets,
references a ledger entry (education, additional information included). Every
bullet is a ledger variant verbatim; new wording must first be added to the
ledger as a `proposed` variant and acknowledged in `selection.yaml`
(decision 2026-10-04-truth-verbatim). As a second check, every number (digits,
spelled-out numbers, `$`, `%`, `~N`, `N+`) traces to the facts the variant
`uses`. Fail on effective conflict or retired, and on unacknowledged single or
proposed.

**Gate.** `make check` = schema + unit tests + golden/determinism render + fit,
ats, and truth on every application whose `meta.yaml` status is `ready`.
`drafting` is unchecked (work in progress must be committable); `submitted` is
frozen: later ledger changes that affect it are warnings in `/status`, not gate
failures; `archived` is ignored (decision 2026-10-04-application-states). The
gate is read-only (decision 2026-10-07-read-only-gate). It passes on a fresh
template copy: placeholder ledger, no applications, no `master/`.

**`rc new-app --company <Co> --role <Role> (--url <url> | --file <path>)`**
scaffolds an application folder and saves the posting. If the fetch fails, ask
the owner to paste the text into a file and rerun with `--file`.

**DOCX renderer**: deferred (STATUS.md).

## 7. Claude skills and commands (in `.claude/`)
Keep each SKILL.md tight and procedural. Every skill reads
`profile/preferences.md` first.
- **onboard-owner** / `/onboard`: first-run setup. Collects the owner's earlier
  resumes into `reference/resumes/`, interviews the owner, builds
  `ledger/ledger.yaml` (diff before every write, `ledger/example.yaml` as the
  shape), writes `profile/preferences.md` and `profile/voice.md`, creates
  `master/selection.yaml`, confirms the remote is private, and ends with
  `make check` green.
- **tailor-resume** / `/tailor <url|file>`: the §1 pipeline. `analysis.md` is a
  matrix: requirement · priority · exact phrases · matched ledger ids · strength
  · notes. `angle.md`: 2–3 options. **Stop.** After the owner's choice: select,
  write, loop `rc fit` until green, then `rc ats` and `rc truth`. Review with a
  fresh-context subagent acting as that company's recruiter, given only the PDF
  text and the posting: what it notices in 6 seconds, what's unclear, what it
  would ask in an interview. Revise if warranted, then record.
- **cover-letter** / `/cover <app>`: research the company with web search (cite
  sources in comments in `cover-letter.md`). The "why this company" paragraph
  must contain something a generic letter couldn't. Ledger facts only. Voice
  from `profile/voice.md`; load any writing skills it names if installed, and
  say so if they are not. Under one page.
- **ledger-update** / `/ledger`: add facts the owner states, resolve questions
  they answer, add variants from shipped resumes (with `uses`). Diff first.
  Never upgrade a status without their answer.
- **/status**: applications by status, plus ledger health (conflicts, singles,
  open questions).

## 8. Build history
Phases 1–6 of the original build (scaffold, ledger schema, template, fit/ATS/
truth checks and gate, skills, cover-letter pipeline) are complete in this
template. What remains is per-owner: onboarding (`.claude/skills/onboard-owner/`),
then applications. Changes to `rc`, templates, or skills follow the same rule
as everything else: `make check` green, a decision record for anything
non-obvious, a STATUS.md section.

## 9. Done means
Fresh copy → `make doctor` installs → `make setup` → `make check` passes on any
machine. CI green. After onboarding: one real application through the full
pipeline, with `report.json` showing every hard constraint passing. STATUS.md
lists what's unverified and what's deferred, each with its trigger.
