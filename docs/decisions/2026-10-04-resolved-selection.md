# Selection resolves to a literal file before rendering

`selection.yaml` holds ledger ids and layout levers. `rc` resolves it into
`build/resolved.yaml` (text plus ids). `templates/resume.typ` reads only the
resolved file.

Why: the golden test renders fixed text whatever that text's ledger status (a
reference resume can contain retired or conflict content). As a resolved
fixture it bypasses the truth check by construction instead of by exemption.
It also keeps the Typst template free of ledger-schema logic, so schema changes
never touch layout.
