# The gate is read-only and fails on stale artifacts

`rc gate` re-rendered every `ready` application and rewrote its PDF and
`report.json` in place. With several sessions working at once, one session's
ledger edit plus `make check` dirtied applications other sessions owned, and
those stray changes blocked a rebase (CONTRIBUTING.md, "Files that are
generated and committed"). CI never noticed, because it compared nothing to the committed copies.

- **Default `rc gate`** renders into `build/apps/<slug>/gate/` and writes nothing
  under `applications/`. It then compares against what is committed: each
  `report.json` section it computed must equal the committed one, and each PDF
  must match by bytes or, failing that, by extracted text. Any mismatch is
  `STALE` and fails the gate.
- **Text, not bytes, decides for PDFs.** Layout drift already shows in
  `report.json[fit]` (line counts, last-line fill, levers), and text survives
  platform differences in PDF metadata between macOS and CI's Linux.
- **`rc gate --write`** keeps the old behavior for the deliberate case: a ledger
  change that legitimately moves other applications. The session runs it in its
  own worktree and commits the diff with the change.
- `rc fit/ats/truth/cover <app>` still write: they act on the one application in
  hand.

Consequence: a ledger edit that changes a variant a `ready` application uses
now fails CI until that application's artifacts are regenerated and committed.
That is the point: the committed PDF is the one the owner uploads.
