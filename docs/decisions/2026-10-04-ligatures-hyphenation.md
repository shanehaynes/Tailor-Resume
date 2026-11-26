# Ligatures and hyphenation off

Experiment (2026-10-04, Typst 0.15.1 + Carlito): with ligatures **on**, `pdftotext`
still extracted "workflow", "office", "fiscal" correctly. Typst writes proper
Unicode mappings for ligature glyphs. So the ligature risk to a good parser is
lower than first assumed.

Ligatures stay **off** anyway. Employer parsers vary in quality, the cost is zero,
and the smoke test enforces it. Hyphenation stays off for a separate reason: a
keyword split across lines ("integ-/ration") breaks exact-match keyword search
in every parser.
