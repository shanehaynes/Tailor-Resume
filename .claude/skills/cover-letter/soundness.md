# Soundness review (the last gate before the owner sees a letter)

Why it exists: a line can sound right and say the opposite of what is true.
Rhetoric passes voice checks; only a reader who restates every claim plainly
catches it.

## Rules
- It runs **after** the voice review and **after every edit**, including its own
  fixes. On a re-run, check the changed sentences plus their consistency with the
  rest, and give the reviewer the paragraph AND the sentences that define its key
  terms (a lone paragraph produces false "no antecedent" flags).
- Stop when the verdict is "sound", or after 4 passes. Anything still flagged
  after the cap goes to the owner as an open item, not another pass.
- Soundness beats voice. A sentence that fails here is rewritten plain or cut,
  however good it sounds.
- Fresh-context subagent, no tools. Give it: the letter without comments; the
  facts each claim rests on (from the cited ledger facts, in plain words, plus
  what is NOT known, e.g. "no baseline measured, team size unknown"); the rule that
  facts about the owner and quoted company text are given, and everything else is
  its target.

## The method it applies to every non-fact sentence
1. **Paraphrase test.** Restate the sentence literally. Flag it if the plain version
   is false, trivial, vague, or a different claim from what the rhetoric implies.
2. **Argument map.** Premises (FACT / QUOTE / AUTHOR'S CLAIM) -> conclusion. Does it
   follow? Where is the gap?
3. **Consistency.** Does any claim contradict or strain against another, especially
   across paragraphs?
4. **Equivocation.** Does a key term shift meaning ("customer" = shipper in one
   place, consignee in another; "on time" = pickup in one place, delivery in another)?
5. **Overclaim.** Absolutes, "decides", "the answer is", causal claims stronger than
   the reasoning.
6. **Objection.** Is it the strongest form, and does the reply answer all of it?
7. **Implied facts.** Does juxtaposition imply something about the owner's work that
   the ledger doesn't say (e.g. a principle placed right after a result reads as the
   method that produced it)?

It returns: argument map, each flagged sentence with its failure named and a sound
rewrite (no new facts, no derived numbers) or "cut", and a verdict: sound / sound
with fixes / unsound thesis. It flags real failures only, never phrasing preferences.

## What to do with its output
- Apply fixes that hold up. Check its rewrites yourself: reviewers also invent
  (e.g. asserting a system worked "exactly" some way, or for some reason, that the
  ledger doesn't say).
- An implied fact that would help if true becomes a question for the owner, never
  wording.
