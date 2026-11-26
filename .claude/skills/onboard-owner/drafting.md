# Drafting the ledger from sources

Shape: `ledger/example.yaml` (fictional; copy its structure, never its content).
Schema: `ledger/schema.json`. Keep the header comment of `ledger/ledger.yaml` (it
defines the statuses and variants); change its title line from "placeholder" to
the owner's name, replace the "This file ships empty" paragraph with one line on
what the ledger holds, and fill its `Seeded` line: date, number of sources,
version ids.

## Loop, one section at a time
1. First section only: `mkdir -p build/onboard && cp ledger/ledger.yaml build/onboard/ledger.yaml`.
2. Edit the section in `build/onboard/ledger.yaml`.
3. `uv run rc ledger check build/onboard/ledger.yaml`; fix until it passes.
4. Show the review table (below) and
   `git diff --no-index --stat ledger/ledger.yaml build/onboard/ledger.yaml`.
   During onboarding the table plus the stat is the diff CLAUDE.md invariant 3
   requires (a whole section is too long to read as YAML). Show the full hunks
   (`git diff --no-index ledger/ledger.yaml build/onboard/ledger.yaml`) if the
   owner asks, and offer to open the draft in their editor. Wait for approval;
   apply corrections.
5. `cp build/onboard/ledger.yaml ledger/ledger.yaml`, `uv run rc ledger check`,
   commit `ledger: onboarding <section>`.

## Review table
| id | claim (shortened) | status | sources |
|---|---|---|---|

Then per accomplishment: variant count and which versions shipped each; then the
open questions this section created. Never the raw YAML.

## Ids
- Pattern `^[a-z0-9]+(-[a-z0-9]+)*$`. Question, education, employer, role,
  accomplishment, and project ids are unique across the ledger; fact and variant
  ids are unique within their accomplishment.
- Education `edu-<school>`; employer a short name; role `<employer>-<role>`;
  accomplishment names the work (`dock-scheduling`), not the verb; fact ids name
  the claim (`team-size`, `late-loads-cut`); variant ids are the version id that
  shipped them (`2024-ops`), or `proposed-1` for new wording; questions `q-<topic>`.

## Contact
From the newest source until Part B settles the name as it should appear
(preferred or legal) and the items to show. If sources show different phones,
emails, or links, ask which to use (a choice, not a fact conflict). Links must
start with `https://`. `website` holds a portfolio or personal site (label
"Website"); `blog` only a blog (label "Blog"). `location` is city and state (or
region), as the owner wants it shown; never a street address.

## Education
`school`, `location`, `degree` as shipped, `end` (year; expected year for
students), `facts` (each honor, scholarship, club role, GPA, test score is its own
fact; `display` holds the shipped short wording when it differs from `claim`).
`degree_variants`: each shipped degree line verbatim (id: the version id that
shipped it); a two-line title is `First line | second line`. Shipped wording is
`proposed` until the official title is confirmed from a transcript, diploma, or
the owner's words. Once it is, add the official title as a single-line variant
tagged `default` and, if it is long, a two-line one tagged `layout-alt`; each is
`confirmed` once the owner approves its exact text. Tailoring uses the `default`
variant unless preferences name another. `major_official`, `emphasis_official`,
`second_major_official` only from those same sources. A degree in progress: `end`
is the expected year, and a fact says so ("Expected May 2027").

## Experience
Employer: `company`, `descriptor` (optional; only as shipped or in the owner's
words; note where any number in it comes from), `location`, `roles`. Role:
`title` and `dates` exactly as shipped ("Jun 2022 - Present"); `note` for
anything the owner said about it (a gap before it, an official vs used title).
A promotion is a new role.

## Summary, objective, profile text
Split its checkable claims into facts on the matching accomplishment or
education entry. Years of experience is `derived` from role dates; ask before
using it. Adjectives ("compassionate", "detail-oriented") are not facts; drop
them. The paragraph itself is not a variant: the template has no summary
section. If the owner wants one, it is a `feat/` schema and template change; say
so in Phase 6.

## Accomplishments: variants and facts
One accomplishment per piece of work (a project, initiative, or recurring duty),
not per bullet. Three versions describing one project give one accomplishment
with three variants.

**Variants** hold every source bullet verbatim, character for character. Typos
stay; flag them as a question instead of fixing them. Identical text in several
versions is one variant with `used_in: [every version id]`; any difference makes a
separate variant. Shipped wording carries no explicit status unless a resolved
fact makes it false (`retired`) or contested (`conflict`). A header bullet with
sub-bullets that always ship together is a `groups` entry.

**Facts** are atomic: one checkable claim each. Split every variant into its
action and verb (led, built, analyzed, recommended), scope (team, region, client
count), each number with unit and timeframe, outcome, and tool. Then:
- `uses` on the variant lists every fact its wording relies on, verbs included.
- Numbers trace by token, so write a fact's number in the form the variants use:
  `$1.2M` does not match `$1,200,000`, nor `40%` match `40 percent`. Number words
  two through twelve normalize to digits; "one" is not counted.
  `rc ledger check` fails any variant whose numbers are missing from its facts.
- `source`: the version ids the claim appears in.
- `summary` (accomplishment): one line on what the work was.
- `gaps` (accomplishment): what the owner says is NOT true, once known.

## Statuses
| Situation | Status |
|---|---|
| Same claim in 2+ sources, none disagreeing | `consistent` |
| One source only | `single` |
| Sources disagree | `conflict`: each competing claim is its own fact, plus an open question naming both ids |
| The owner stated it in this session | `confirmed`, note `owner YYYY-MM-DD: '<their words>'` |
| Computed from other facts | `derived` with `derivation`; only numbers the owner has seen and approved |
| Shown false | `retired` with a dated note; never delete |

Disagreements that are conflicts: "led" vs "supported"; 30% vs 35%; "saved" vs
"projected to save"; "launched" vs "piloted"; different titles or dates for one
role. Not a conflict: one version omits a detail another has. That is two facts.

Wording you write is a variant with `status: proposed`. The owner's explicit yes
to that exact wording removes `proposed` (note it with their words).

## Open questions to create while drafting
- Every conflict (name both fact ids in the note).
- Every vague or unanchored metric: "significantly", "improved efficiency", a
  number without unit, timeframe, baseline, or measurement method.
- Every claim an interviewer will probe: leadership and ownership verbs, "first",
  "only", "launched", strategy, revenue or savings attribution.
- Missing or inconsistent dates and titles.
Format: `{id: q-<topic>, question: "<as you will ask it>", note: "<fact ids it affects>"}`.

## Projects, additional, inventory
- Project: `name`, `dates`, `url` (https or null, with `url_note` if null),
  facts, variants. A variant that links the name must start with the name.
- `additional.certifications`, `languages`, `lecturing`, `awards`, `publications`,
  `volunteering`, `memberships`: facts (`display` for the shipped short form). Ids
  are unique across all of these lists. A license is a certification: type,
  issuing state or body, status, expiry in the claim; never its number.
- `additional.skills`: grouped keys (`analysis`, `software`, `methods`), items as
  shipped. Items the owner calls familiar but unused go under a `familiar_only`
  key and are never selected (convention only: `rc` treats every key as
  inventory, so check selections for it).
- `additional.interests`: strings, verbatim.
- `version_index`: version id -> file name, with a comment on what it targeted.
