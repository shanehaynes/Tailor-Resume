# Variants declare the facts they use; status is derived

Each fact gets an id; each variant lists `uses: [fact ids]`. A variant's
effective status is the worst of its explicit status and its facts' statuses:
retired > conflict > {single, proposed} (need acknowledgment) > {confirmed,
consistent, derived} (clear).

Why: hand-set variant statuses drift from the facts (a variant that relies on a
`single` fact can easily carry no status at all). Derivation makes "single needs
acknowledgment" enforceable.

Limit: `uses` can't capture a claim no fact states. Those are listed for the
owner when a ledger is built or migrated, and stay explicit on the variant
(`status`).
