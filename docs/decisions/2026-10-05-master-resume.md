# Master resume: a full-length reference rendered from the ledger

`master/selection.yaml` (created during onboarding) selects every role and
accomplishment in the ledger, each with its fullest variant whose effective
status is clear or acknowledged, plus every education fact, certification,
skill, and language. `make master` runs `rc truth master` and renders
`master/resume.pdf` through the same resolver and template as applications, so
every line is ledger text verbatim.

It is not an application: it lives outside `applications/`, so the gate never
fits it, and no one-page, two-line, or orphan constraint applies (it usually
runs two pages). Tailored resumes are cut from it, not copied from it.

Consequences accepted:
- Acknowledgments for proposed items are carried from the application
  selections where the owner gave them. A new proposed variant still needs its own.
- The resolver has no group-header rendering, so a project described by two
  variants either repeats its name or splits name/link and detail across the
  two bullets. Add header support if this ever ships outside the reference.
- Facts without any variant do not appear. Writing wording for them is a ledger
  change, not a master-resume one.
