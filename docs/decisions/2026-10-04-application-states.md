# Application states gate differently

`meta.yaml` status: `drafting` (not gated, so mid-fit-loop work can be
committed), `ready` (fit, ats, truth gated), `submitted` (frozen; ledger drift
that affects it surfaces as a `/status` warning, because a shipped PDF can't be
changed and unrelated commits shouldn't be blocked), `archived` (ignored).
