# Status

## Template state
Not yet onboarded. Run `/onboard`. Onboarding writes `profile/preferences.md`
and `profile/voice.md`, fills `ledger/ledger.yaml`, and appends its own
section below. When it finishes, it replaces this paragraph with one line,
`Onboarded YYYY-MM-DD (see Onboarding).` Every later session appends a section
(CLAUDE.md, Conventions).

## Verified (template)
- `make check` green on a clean clone of the template (macOS): placeholder
  `ledger/ledger.yaml`, the fictional `ledger/example.yaml`, unit tests, golden
  render, and a gate with no applications.

## Not verified
- CI (GitHub Actions, Linux) runs the same `make check`; no run yet on this
  repository. Trigger to act: the first push.
- poppler is unpinned (Homebrew on macOS, apt on CI). ATS checks that use
  `pdftotext` rely only on version-stable properties. Trigger to act: the first
  `pdftotext` output that differs between local and CI.
- `scripts/setup.sh` on macOS x86_64 and Linux arm64 (checksums recorded,
  never run).

## Known limitations
- US Letter only. Trigger: an application that requires A4.
- DOCX renderer deferred. Trigger: a portal that requires .docx.
- Number tracing reads digits and English spelled-out numbers only; resumes
  and letters in other languages are untested.
- Spelled-out counts in letters ("three habits") fail the number trace. Kept
  strict on purpose; revisit if it blocks real wording often.
- Additional-information lines are measured, not constrained. Trigger: a
  wrapped skills line looks wrong in a review.
