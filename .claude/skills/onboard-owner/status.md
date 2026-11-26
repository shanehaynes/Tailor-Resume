# The onboarding progress record

Lives in STATUS.md (create it if missing) on the `chore/onboard` branch, as one
section updated in place at every checkpoint. Only this branch edits it, so the
union merge on STATUS.md never duplicates its lines. After Phase 6 merges, later
sessions append sections as usual.

```markdown
## Onboarding (started YYYY-MM-DD)
Workflow: parallel | single. Remote: <owner/repo>, PRIVATE (checked YYYY-MM-DD) | local <path>.
Template remote: <owner/repo>; shares history: yes | no (first update merge needs --allow-unrelated-histories).
Targets: <roles; industries; level>. Sample postings: build/onboard/postings/ (<n>).
Best current resume: <version id>. Cover letters: yes | no.

- [x] 0 Environment and privacy (YYYY-MM-DD): macOS arm64, checks green
- [x] 1 Sources (YYYY-MM-DD): 4 versions; 2 local only (.git/info/exclude)
- [ ] 2 Ledger: contact, education done; experience 1 of 3; projects, additional, skills, interests to do
- [ ] 3 Interview: 
- [ ] 4 Preferences
- [ ] 5 Voice
- [ ] 6 Master resume
- [ ] 7 Dry run

| Version id | File | Date | Targeted | Notes |
|---|---|---|---|---|
| 2024-ops | 2024-ops.pdf | 2024-03 | operations analyst | best current |

Counts (rc status): conflicts 0 | singles 12 | needs-ack variants 5 | open questions 7
Next: <the single next step, so a new session can resume cold>
```

Rules: a phase is checked only at its checkpoint, with the date and one fact
that proves it. "Next" is always one concrete step. Record a skipped phase as
checked with the reason ("skipped: no cover letters"). Phase 3 records why the
interview stopped ("owner stopped" or "remaining questions unlikely to ship").
At Phase 7, the STATUS.md `## Template state` section becomes one line:
`Onboarded YYYY-MM-DD (see Onboarding).`
