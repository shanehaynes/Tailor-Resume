# Tailor-Resume

Tailors one-page resumes and writes cover letters for the owner of this copy
from a verified career ledger, with layout **measured from rendered PDFs**,
never estimated. Full spec: `docs/spec.md`. Current state: `STATUS.md`. The
owner's preferences: `profile/preferences.md`; cover-letter voice:
`profile/voice.md` (if it exists). Read them before working.

## First run
If `profile/preferences.md` does not exist, this copy has not been set up.
Before any other work, tell the owner and run the onboard-owner skill
(`/onboard`). Do not tailor, write letters, or edit the ledger until onboarding
has finished.

## Maintaining the template itself
If origin is the public template (`gh repo view --json isTemplate -q .isTemplate`
prints `true`) and the owner says they are maintaining the template, skip
onboarding and invariant 8: this repo is meant to be public. It holds no
personal data, ever: examples and tests use only the fictional person in
`ledger/example.yaml`; `ledger/ledger.yaml` stays the placeholder; no
`profile/preferences.md`, `profile/voice.md`, `master/`, `applications/`, or
files in `reference/resumes/` besides its README.

## The owner's profile
- `profile/preferences.md`: written during onboarding; changed only on the
  owner's word in the current session. Positioning, formatting rules (what
  never to list, degree form), where finished PDFs are copied, and the session
  workflow (the line `- Workflow: single` or `- Workflow: parallel`). Every skill reads it
  before tailoring or writing; it overrides skill defaults, never the invariants.
- `profile/voice.md`: the owner's cover-letter voice. `/cover` reads it.
- `profile/*.example.md` and `ledger/example.yaml` show the shape only. The
  example ledger is fictional (tests use it); never draw a fact from it.

## Commands
- `make setup`: pinned typst → `bin/`, `uv sync`. `make doctor`: system prereqs.
- `make check`: **the gate**. CI runs exactly this. Must pass before every commit.
  `rc gate` is read-only (renders into `build/`) and fails on stale PDFs or
  `report.json`; `rc gate --write` regenerates them in place.
- `uv run rc ...`: `ledger check`, `new-app`, `fit <app> [--solve]`, `ats <app>`,
  `truth <app>`, `cover <app>`, `gate`, `status`. Workflows: `/onboard`,
  `/tailor`, `/cover`, `/ledger`, `/status` (skills in `.claude/skills/`).
- Always render through `rc.paths.typst_compile_args` (pinned binary,
  `--font-path fonts --ignore-system-fonts`). Never call a global `typst`.

## Session workflow
Chosen during onboarding and recorded in `profile/preferences.md`. No file, or
no `Workflow:` line, means single. The guard hook reads the same line.

**Single** (`workflow: single`): one session at a time, on `main` in the
checkout. `make check` before every commit; one concern per commit
(`app: <slug>`, `ledger: <what>`, `feat:`/`fix:`/`chore:`). Push if the copy
has a remote.

**Parallel** (`workflow: parallel`; several sessions at once; details in
CONTRIBUTING.md):
- Start every task with `scripts/git-new.sh <app|ledger|feat|fix|chore>/<slug> "<intent>"`
  and work only in the worktree it prints. Read its list of other sessions' claims.
- The primary checkout stays on `main`, clean, fast-forward only (`git pull --ff-only`).
  Never commit, rebase, merge, or run `rc fit/ats/truth/cover/new-app` there.
- Finish: `make check`, push the branch, `gh pr create`, `scripts/combine-check.sh`.
  **The owner merges.** If the PR conflicts, merge `origin/main` into your
  branch in your worktree; never rebase a pushed branch.
- `scripts/supervisor-report.sh`: read-only sweep of what has gone stale.

**Both:**
- Never `git stash` bare/pop/drop, `reset --hard`, `clean -f`, or force-push
  without reading what you would destroy; a guard hook blocks them
  (`RC_DESTRUCTIVE_OK=1` after you have looked). Set work aside with a WIP commit.
  The guard's primary-checkout rules apply only under `workflow: parallel`.
- Resume and cover-letter PDFs stay in their application folder; upload from
  there. Never copy them to the repo root. If `profile/preferences.md` names a
  folder outside the repo for finished PDFs, copy them there as well.

## Invariants (non-negotiable; enforce in code where the spec says so)
1. `ledger/ledger.yaml` is the only source of facts. Every resume bullet
   references an accomplishment id. Every number in a bullet appears in that
   accomplishment's facts.
2. `status: conflict` blocks a build. `status: single` needs the owner's written
   acknowledgment in the application's `selection.yaml`. `retired` variants never ship.
3. Never invent, inflate, or "resolve" facts. Never change a status or close an
   open question without the owner's answer in the current session. Show a diff
   before every ledger write.
4. Mirror job-posting language only where a ledger fact supports it. A missing
   keyword gets reported as a gap.
5. The positioning-angle choice is the owner's. Stop at that checkpoint every time.
6. Layout floors: body ≥ 10pt (≤ 11pt), margins ≥ 0.5in. Lever order: content →
   spacing → margins → font size. Content is never edited automatically.
7. The ledger travels only as a file under git, never by pasting into chat.
8. This copy holds the owner's personal data. Its remote must be private:
   before pushing, check `gh repo view <owner>/<repo> --json visibility` for
   origin's repo; if it is public, stop and tell the owner. An origin that is a
   local path (a bare repo on this machine) satisfies this.

## Layout targets
One page; usable height ≥ ~95% filled; every bullet ≤ 2 lines; a bullet's last
line ≥ ~35% of the line width (no orphans); single column; standard headings;
ligatures and hyphenation off. Default look: `templates/resume.typ` (Carlito
10.5pt, 0.6in side margins); choices in
`docs/decisions/2026-10-04-template-fidelity.md`.

## Conventions
- Decision records: `docs/decisions/YYYY-MM-DD-slug.md`. Write one for any
  non-obvious choice.
- Applications: `applications/YYYY-MM-DD-company-role/` (layout in spec §5).
- `reference/resumes/` holds the owner's earlier resumes, added during
  onboarding: read-only historical inputs. Never edit them.
  `reference/measurements.md` describes the template's default look; it changes
  only with a template change (`feat/` branch).
- Update `STATUS.md` at the end of every working session (append a section;
  it union-merges).
