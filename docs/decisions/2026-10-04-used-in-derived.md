# Usage is derived, not written to the ledger

Each application's `selection.yaml` already records the variants it used, so `rc`
computes usage from `applications/`. Writing `used_in` back would make every
application a ledger write needing a diff and approval, for bookkeeping.
`used_in` values recorded when the ledger is built (which earlier resumes in
`reference/resumes/` a wording came from) are history and stay as they are.
