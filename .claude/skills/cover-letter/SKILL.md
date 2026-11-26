---
name: cover-letter
description: Write the owner's cover letter for an application folder from ledger facts and cited company research, checked by `rc cover`. Use for /cover, or when the owner asks for a cover letter for a posting they're tailoring to.
---

# Write a cover letter

Format and checks: the docstring of `rc/cover.py`. Work in `applications/<slug>/`:
on `main` under the single workflow; under parallel (CONTRIBUTING.md), in the
application's worktree if its branch is still open, else
`scripts/git-new.sh app/<slug>-cover`.
The resume (selection.yaml, angle.md, analysis.md) should exist first; the letter
argues the same angle and must not contradict it.
Read `profile/preferences.md` for the owner's standing rules (things never to claim
or name, wording preferences, where finished PDFs go) and apply them throughout.

1. **Load the owner's voice** and read `voice.md` (this folder): it says how to use
   `profile/voice.md`, and how to derive one if it is missing. Also load any writing
   skills the owner has installed (style, vocabulary, editing); if there are none,
   continue.
2. **Research the company** with WebSearch, then read primary sources (the
   company's own pages, filings, product docs, executive posts) with the browser's
   `get_page_text`. Never cite a search snippet or WebFetch summary as a quote.
   No browser tool available: use WebSearch and WebFetch only to find the pages,
   then ask the owner to paste the primary-source text you want to quote; without
   it, refer to the source in your own words and cite only its URL.
   Find something a generic letter couldn't say: a product decision, a stated
   strategy, a customer segment that connects to a ledger fact. Record each source
   as `<!-- source: URL | "verbatim quote" -->`; research notes go in comment-only blocks.
3. **Draft** under one page (~300-380 words), four short paragraphs:
   - Opening: the role and the one-line thesis from angle.md. No "I am writing to".
   - Proof: two or three ledger facts that carry the angle, with their numbers.
   - Why this company: the specific thing from step 2, tied to a ledger fact.
     This paragraph must fail the test "could this be sent to a competitor?"
   - Close: what the owner would do in the role; a plain sign-off.
   Every claim about the owner cites `<!-- ledger: acc.fact, ... -->` on its paragraph.
   Ledger facts only: no invented scope, adjectives that inflate, or numbers not in a
   cited fact. Mirror the posting's words only where a fact supports them.
4. **Check**: `uv run rc cover <app>` until PASS (numbers trace, statuses, one page).
   Treat its warnings: a long uncited paragraph is usually an unsupported claim.
5. **Write in the owner's voice**: apply `profile/voice.md`, including its
   "Transposing to a cover letter" section. The letter argues the angle's thesis;
   facts serve it. Cut a fact that doesn't (the resume carries it).
6. **Voice review** with a fresh-context subagent. Give it only: the voice profile
   (`profile/voice.md`), 3-4 short excerpts of the owner's own writing (from the
   samples named in profile/voice.md), and the letter text without comments. Tell it
   it may not add or strengthen any claim about the owner, and must keep quotes from
   the company verbatim. Ask for: traits hit/missed with quotes, the three weakest
   sentences rewritten, generic or template lines and lines that sound unlike the
   owner, whether the proof paragraph serves the thesis, and a verdict (send / revise lightly / revise
   substantially).
   Apply what holds up; reject any rewrite that adds a fact or a derived number
   (e.g. "a third" from 33%). Rerun `rc cover`. Keep the prior draft in build/.
7. **Soundness review** (`soundness.md`, this folder): the last gate. Runs after the
   voice review and again after every edit, until the verdict is "sound". Soundness
   beats voice. Turn any helpful implied fact into a question for the owner.
8. Show the owner the letter text (not the comments), the sources, and what the voice
   and soundness reviews changed. Commit `app: <slug> cover letter`. Single: push
   `main` if there is a remote. Parallel: push the branch and open or update the PR;
   the owner merges. It ships only with their approval.
