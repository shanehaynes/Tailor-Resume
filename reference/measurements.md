# The default look (templates/resume.typ)

What the template renders at its default levers, measured with pdffonts and
pdfplumber (`scripts/measure.py <pdf>` prints line geometry; `scripts/compare.py
<a.pdf> <b.pdf>` pairs the lines of two PDFs and prints the deltas). This is the
template's shipped look, not anyone's resume. Onboarding may tune the fixed
geometry to match the new owner's existing resume (measure theirs, compare,
adjust `templates/resume.typ`, regenerate `tests/golden/`) on a `feat/` branch;
record the owner's original in a decision record, and update this file only
where the template's defaults change.

## Page and type
- Page: US Letter, one page, single column.
- Font: **Carlito** (Regular, Bold, Italic, BoldItalic), metric-compatible with
  Calibri, committed under `fonts/`. System fonts are ignored at render time.
- Ligatures, kerning, hyphenation, and smart quotes are off (ATS round-trip).
  A hyphenated word never splits across lines.
- Name: Bold, 18/10.5 of the body size (18pt at the default), uppercase.
- Contact line: body size, pipe-separated; GitHub, LinkedIn, Blog, and Website
  render as hyperlinked words, email as a mailto link. Links are blue and
  underlined.
- Section headings: faux small caps. First letter of each word at body size,
  remaining letters at 8.5/10.5 of it. A 0.7pt rule runs under each heading.
- Body: Carlito 10.5pt. Bold for org names (uppercase), titles, dates, and
  locations; locations and dates right-aligned to the text margin.
- Org descriptor ("Regional freight carrier, 1,200 employees" in the example):
  BoldItalic at 9/10.5 of the body size, inline after the org name.
- Bullet glyph "•" at 9/10.5 of the body size; text hangs 20pt after it.
- Name, headings, bullets, and additional-information lines sit 6pt inside the
  text margin.

## Geometry at the default levers
| Lever | Default | Floor / range |
|---|---|---|
| Body size | 10.5pt | 10 to 11pt |
| Left/right margin | 0.6in (43.2pt) | ≥ 0.5in |
| Top margin | 0.6458in | ≥ 0.5in |
| Bottom margin | 0.5in | ≥ 0.5in |
| Leading (within a paragraph) | 2.7pt | 1.8 to 4.0 |
| Entry gap (between orgs, roles) | 6pt | 3 to 10 |
| Section gap | 10pt | 6 to 14 |

Bullet line pitch is about 12.5 to 13.2pt at the defaults. The full lever list
and bounds live in `rc/fit.py` (SPACING, MARGIN_V, MARGIN_X, FONT).

## Lever order and targets
Content first, then spacing, then margins (vertical, then horizontal), then font
size; content is never edited automatically. Targets: usable height ≥ ~95%
filled, every bullet ≤ 2 lines, a bullet's last line ≥ ~35% of the line width.
Font size is the lever of last resort: across hand-made resumes it tends to
drift (9.5 to 11.5pt) to make content fit, which is what the floors exist to
stop.

## The example golden
`tests/golden/` renders the fictional example (ledger/example.yaml) at these
defaults: one page, about 87% filled before the solver moves spacing.
