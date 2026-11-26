# Stakes and stack

**Stakes.** Lifespan: product (months to years, across recruiting seasons).
Who works on it: one owner per copy, plus Claude Code sessions: one at a time
by default, several at once if the owner chooses the parallel workflow
(CONTRIBUTING.md). Data: the owner's own personal data (contact info, a
detailed career ledger), so **each owner's copy must be private**. The template
itself holds only fictional data. Reach: local only; nothing deployed.

**Stack.**
- Renderer: Typst, pinned (`.typst-version`, `scripts/typst-checksums.txt`),
  installed per machine into `bin/` by `make setup`. Considered: LaTeX (slow,
  painful to drive from code); Word/docx (layout not measurable from code).
- Python tooling via uv with a committed `uv.lock`. Measurement uses pdfplumber
  on the rendered PDF; ATS checks use poppler's `pdftotext`.
- One gate: `make check`, run identically locally and in CI (GitHub Actions, Linux).

**Why pinning matters.** Line breaks depend on engine version and font metrics.
A fit measured on one machine has to hold on every machine, so both are pinned
and system fonts are ignored at render time.
