# Template: choices that make the Typst render match a Word/ReportLab resume

Measured during the original build against a ReportLab reference PDF with
scripts/compare.py: every line's baseline within 0.0pt, every line break
identical, pdftotext output identical.

- **Greedy line breaking** (`linebreaks: "simple"`). Typst's default optimal
  (Knuth-Plass) breaking differs from ReportLab and Word, so measured fit would
  not predict what the owner has seen in Word.
- **Kerning off.** ReportLab and Word (default) don't kern; widths match only
  with it off. Text layer unaffected.
- **No break inside hyphenated words** (`box` around `\w+(-\w+)+`). Typst breaks
  at hard hyphens even with hyphenation off ("data-|driven"), which splits
  a keyword in the text layer.
- **Faux small caps** (uppercase at 10.5/8.5pt) rather than `smallcaps()`: real
  small caps can extract as lowercase.
- **Smart quotes off; font fallback off** (Typst embeds fallback fonts; a missing
  glyph must fail visibly, not render in another face). `document(date: none)`
  so renders carry no timestamp.
- **Colon after a bold label is regular weight**, as in the reference.
- **Contact line 10.5pt**, as measured (an earlier hand measurement said 9pt).

Known residual: a line exactly as wide as the text column stays on one line in
ReportLab and wraps in Typst on the tie. Not fudged; text output is identical
either way.

Degree layout: the **single-line** form ("Bachelor of Science: <majors>") is the
default look. The two-line form stays supported and tested; a selection uses it
when the single line doesn't fit or `profile/preferences.md` asks for it, and
otherwise only after asking the owner.
