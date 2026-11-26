# Truth check: bullets ship verbatim from the ledger

The overclaims that matter are usually words, not numbers: "led" for "helped",
"architected" for "built", "saved" for "projected to save", "launched" for
"piloted". A number-only trace passes all of them. So a shipped bullet must be
a ledger variant, verbatim. New wording is added to the ledger as a `proposed`
variant (with `uses`) and acknowledged in the application's `selection.yaml`
before it can ship. Number tracing stays as a second check against the facts
the variant `uses`, with spelled-out numbers normalized ("three years" = 3).

Rejected: a similarity threshold that reports drift. It reports after the fact
and lets a one-word overclaim ship under the threshold.

2026-10-05: spelled-out "one" is no longer read as a number. In letters it is
nearly always a pronoun ("the one that fits"), and every such use failed
the trace. Counts "two" through "twelve" are still traced; a digit "1" still is.
