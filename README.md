# Tailor-Resume

Ledger-backed, measured-layout resume tailoring, driven by Claude Code. You
give it a job posting; it proposes positioning angles, you pick one, and it
builds a one-page PDF (and, if you want, a cover letter) from facts you have
verified, then checks that the PDF fits, parses, and says nothing untrue.

## Why it works this way

- **Writing is judgment; layout is measurement.** A language model cannot see
  where a line wraps. Every layout claim here (one page, bullets at most two
  lines, no orphaned last words, page filled) comes from rendering the PDF with
  a pinned Typst and measuring character positions.
- **Facts are never invented.** Your career lives in one file,
  `ledger/ledger.yaml`: accomplishments, the facts behind them, and approved
  wordings. Every bullet ships verbatim from it and every number traces to a
  fact. A posting keyword you cannot back with a fact is reported as a gap, not
  papered over.
- **You decide.** Positioning, ledger changes, and anything only you can know
  stop and wait for you.

## Requirements

- macOS or Linux. On macOS, first: Xcode Command Line Tools
  (`xcode-select --install`) and [Homebrew](https://brew.sh)
- git, and [gh](https://cli.github.com/) signed in (`gh auth login`)
- [uv](https://docs.astral.sh/uv/), poppler (`pdftotext`), xz, curl
- node (for the git guard hook and its tests; optional but recommended:
  without it the guard does not run)
- [Claude Code](https://claude.com/claude-code)

`make doctor` prints the install command for anything missing.

## Setup

**1. Make your own private copy.** Do not fork: a fork of a public repo is
public. `<template-owner>` below is the GitHub account this repository lives
under. Pick one:

- Recommended: clone, then point it at a new private remote. Your copy keeps
  the template's history, so template updates merge cleanly later.
  ```bash
  git clone https://github.com/<template-owner>/Tailor-Resume.git my-resume
  cd my-resume
  git remote rename origin template
  gh repo create my-resume --private --source . --remote origin --push
  ```
- On GitHub: **Use this template → Create a new repository → Private**, then
  clone it. Or with gh:
  ```bash
  gh repo create my-resume --private --template <template-owner>/Tailor-Resume --clone
  cd my-resume
  ```
  These copies start with fresh history; `/onboard` adds a `template` remote,
  and the first template update needs one extra merge step (it explains).
- Not using git yet? `/onboard` can start from a downloaded ZIP: it creates the
  repository and the private remote with you.

**2. Install and check.**
```bash
make doctor   # prerequisites; prints install commands for anything missing
make setup    # pinned typst into bin/, Python env via uv
make check    # the gate; must pass on the fresh copy
```

**3. Onboard.** Open Claude Code in the repo and run `/onboard`. It asks for
your existing resumes (drop PDFs or DOCX into `reference/resumes/`), interviews
you about your history, builds `ledger/ledger.yaml` with you (showing a diff
before each write), and records your preferences and cover-letter voice in
`profile/`. The ledger is only as good as your answers: numbers you are unsure
of stay marked unsure until you confirm them.

## Daily use

| Command | What it does |
|---|---|
| `/tailor <url or file>` | Analyzes the posting, proposes 2–3 angles, stops for your choice, then builds and verifies the resume |
| `/cover <app>` | Writes the cover letter from ledger facts and cited company research |
| `/ledger` | Adds a fact, answers an open question, or adds a wording |
| `/status` | Applications by status, plus ledger health |

Each application lives in `applications/YYYY-MM-DD-company-role/`: the saved
posting, the analysis, the angle, the selection, the PDF, and a `report.json`
with every measurement. Upload the PDF from that folder.

## Privacy

Your copy holds your career data: contact details, employers, numbers. Keep the
repository private. Never make it public, and never open a pull request from it
to the template. `ledger/example.yaml` is a fictional person used by the tests;
your data goes only in `ledger/ledger.yaml`, `profile/`, `reference/resumes/`,
and `applications/`.

## More

- `CLAUDE.md`: the rules Claude follows here.
- `docs/spec.md`: architecture, checks, and acceptance criteria.
- `docs/decisions/`: why each non-obvious choice was made.
- `CONTRIBUTING.md`: running several Claude sessions at once (optional).
