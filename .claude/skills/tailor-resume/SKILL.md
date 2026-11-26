---
name: tailor-resume
description: Tailor the owner's one-page resume to a job posting from the career ledger, with layout measured from the rendered PDF. Use for /tailor, or whenever the owner gives a posting URL or text and asks for a resume, an application, or "tailor this".
---

# Tailor a resume

Invariants are in CLAUDE.md; reread them. Selection format: `selection.md` (this folder).
The owner's standing rules (things never to list, wording preferences, target roles,
where finished PDFs go): `profile/preferences.md`; read it and apply it throughout.
Work in `applications/<slug>/`. Run every `rc` command as `uv run rc ...`.

## 0. Where to work
The workflow is the `Workflow:` line in `profile/preferences.md` (CLAUDE.md).
- **Single:** work on `main` in the checkout; `git pull --ff-only` first if it has a remote.
- **Parallel** (CONTRIBUTING.md): `scripts/git-new.sh app/<company>-<role-short> "<Company> <Role>"`,
  then work only in the worktree it prints. If another session has claimed the same
  company, stop and ask the owner.

## 1. Capture
- `rc new-app --company "<Co>" --role "<Role>" --url <url>`.
- If it says fetch failed: get the page text with the browser tool's `get_page_text`,
  write it to `build/posting.txt`, and rerun with `--file build/posting.txt`. Never
  WebFetch (it returns a summary, not the verbatim posting). If that fails too, ask
  the owner to paste the text.
- Trim site chrome (navigation, related jobs, footers) from posting.md so only the
  posting remains: title through pay/EEO text. Delete lines only; never edit the
  posting's own words. Note the trim in an HTML comment under the capture line.
- Add `deadline:` to meta.yaml if the posting states one.

## 2. Analyze -> `analysis.md`
One table, exactly these columns (rc ats parses it):

| Requirement | Priority | Exact phrases | Matched ledger ids | Strength | Notes |

- One row per requirement, ranked: `must` (stated as required or repeated), `strong`
  (preferred), `nice`.
- Exact phrases: terms an ATS would match, 1-3 words, verbatim from the posting,
  each in "double quotes" ("cross-functional", "experimentation"), not whole clauses.
- A requirement the ledger confirms absent gets its own row with ids `—`, so it
  reports as a ledger gap, not a wording gap.
- Matched ledger ids: accomplishment ids (or `acc/variant`) whose **facts** support
  the requirement; `—` if none.
- Strength: `strong` (a confirmed fact matches directly), `partial` (adjacent), `gap`.
- Below the table: **Ledger gaps** (requirements with no supporting fact; never
  fill them with invented wording) and **Questions for the owner** (facts they might
  have that the ledger lacks).

## 3. Angle -> `angle.md`, then STOP
2-3 options. For each: a one-sentence thesis; what leads (ordered refs); what's cut;
the trade-off; which `must` rows stay weak; which acknowledgments it would need
(run `rc status` for the needs-ack list). End with your recommendation and why.
**Stop and wait for the owner's choice. Never proceed past this without it.**

## 4. Select and write -> `selection.yaml`
- Only ledger variants, by ref. Prefer variants whose tags match the angle.
- To mirror posting language a fact supports but no variant uses: propose a new
  variant through the ledger-update skill (diff first, the owner approves, `uses` set,
  `status: proposed`). Never put new wording anywhere but the ledger.
- `acknowledge:` entries only with the owner's words from this session, quoted in the
  note with the date. Never acknowledge on their behalf.
- Degree line: the degree variant preferences name, else the one tagged `default`.
  Two-line (a `layout-alt` variant with "|") only if preferences ask for it, or if
  the single line won't fit and the owner agrees.

## 5. Fit loop
- `rc fit <app> --solve` until PASS. The solver moves spacing, margins, font; it
  never touches content. If it says only content can fix it, use its deltas:
  swap to a shorter or longer variant, drop or add a bullet. Rerun.
- Never edit layout.yaml by hand.

## 6. Verify
- `rc ats <app>` and `rc truth <app>` must PASS.
- Keyword report: a `wording gap` means a fact exists but its phrase is unused;
  consider a variant swap or proposal. A `ledger gap` goes to the owner as a question.
- Recruiter skim (skip it if preferences say
  `Recruiter-skim review on every tailored resume: no`): run
  `pdftotext -raw applications/<slug>/resume-<company>.pdf -` and spawn a fresh subagent with only that text and posting.md:
  "You are a recruiter at <Company> screening for this role. Here is the posting and
  a resume's extracted text. In 6 seconds, what do you notice? What is unclear or
  unconvincing? Name three questions you'd ask in a phone screen. Be blunt."
  Revise (back to step 4) if it finds something real. Summarize its read for the owner.

## 7. Record
- meta.yaml `status: ready`; append a STATUS.md section; `make check` green
  (if it reports STALE for other apps after your ledger change, `rc gate --write`,
  read the diff, include it); commit `app: <slug>`.
- Single: push `main` if there is a remote. Parallel: push the branch,
  `gh pr create`, `scripts/combine-check.sh`; tell the owner the PR is ready.
  The owner merges.
- If `profile/preferences.md` names a place to copy finished PDFs, copy the resume
  PDF there too, named as its "Name of that copy" line says; the copy in the
  application folder stays the source.
- After the owner says they submitted: `status: submitted`, committed the same way
  (parallel: on a fresh `app/` branch if the old one merged).
- Report: angle chosen, fill, any acknowledgments, keyword gaps, the recruiter's
  read (if it ran).
