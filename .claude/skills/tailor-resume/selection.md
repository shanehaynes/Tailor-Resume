# selection.yaml format

Content only. Every string rendered comes from the ledger; this file picks ids and
structure. Layout levers live in layout.yaml (written by `rc fit --solve`).

The ids below come from the fictional sample ledger, `ledger/example.yaml`; in a real
selection, use the ids in the owner's `ledger/ledger.yaml`.

```yaml
contact: [phone, email, github, linkedin]          # ledger contact keys, in order
acknowledge:                                       # needs-ack refs -> the owner's words
  dock-scheduling/detention: "owner 2027-03-02: 'the 31% is from the finance summary; use it'"
  edu-brookfield/case-comp: "owner 2027-03-02: 'yes, first place, regional round'"
constraints: {min_fill: 0.95}                      # optional overrides
sections:
  - heading: Education
    entries:
      - education: edu-northgate
        lines:                                     # bullets built from facts (display or claim)
          - {facts: [fellowship, gmat], sep: "; "}
          - {facts: [club-lead, clubs], sep: ", "}
      - education: edu-brookfield
        degree_variant: official                   # omit for the bare degree
        lines: [{facts: [honors, case-comp], sep: "; "}]
        bullets: [brookfield-capstone/adopted]     # accomplishment/variant
  - heading: Professional Experience
    entries:
      - employer: harborview                       # descriptor: false to drop the italic line
        roles:
          - role: hv-senior-analyst
            bullets: [route-optimization/short, dock-scheduling/detention, carrier-scorecard/reviews]
          - role: hv-analyst
            bullets: [inventory-forecast/base]
          - role: hv-coordinator
            bullets: [cross-dock/half]
  - heading: Projects
    bullets:
      - {ref: route-ledger/base, link: true}       # links the project name to its ledger url
  - heading: Additional Information
    lines:
      - {label: "Certifications", facts: [lean-green, cpr]}
      - label: "Technical Skills"
        skills:                                    # items must be in the ledger inventory
          - [SQL, Python, Tableau]
          - {label: "Supply chain systems", items: [WMS, TMS]}
      - {label: "Languages", facts: [english, portuguese]}
      - {label: "Other Interests", interests: [Trail running, film photography, "project:field-notes"]}
```

Ack keys: variants `acc/variant`; education facts `edu-id/fact`; degree
`edu-id/degree:variant`; additional facts `additional/fact`.
