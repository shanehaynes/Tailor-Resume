# ATS keyword match: whole words, inflections allowed, acronyms exact

Substring matching reports "ERP" present in a resume because "erp" sits
inside "interpreted". `rc.ats.keyword_pattern` now matches after `norm()`,
case-insensitive:

- **Left edge**: the phrase can't start mid-word (no letter or digit before it).
- **Right edge**: an optional inflection (s, es, d, ed, ing), then no letter or
  digit. Strict `\b` on both ends turns real hits into gaps ("deliver" in
  "delivering", "shipment" in "shipments", "launch" in "launched"); substring
  matching counted those, and a parser that stems would too.
- **Acronyms** (last word all caps in analysis.md: AI, ERP, SQL, CRM) take no
  inflection, so "AI" misses "aid" and "IT" misses "its".
- Hyphens and spaces are boundaries: "AI" hits "AI-powered"; "end-to-end" still
  needs the hyphens. A phrase edge that isn't alphanumeric gets no boundary check.

Not fixed: matching stays case-insensitive, so "IT" hits the pronoun "it"
("ran it"). Fix if an IT phrase decides a must row: match acronyms
case-sensitively.
