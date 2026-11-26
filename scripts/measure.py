"""Dev aid: print line-level geometry of a PDF page (pdfplumber), for template tuning."""
import sys

import pdfplumber

with pdfplumber.open(sys.argv[1]) as pdf:
    print("pages:", len(pdf.pages))
    p = pdf.pages[0]
    lines = {}
    for c in p.chars:
        lines.setdefault(round(c["top"] + 0.75 * c["size"], 1), []).append(c)  # group by baseline
    for base in sorted(lines):
        cs = sorted(lines[base], key=lambda c: c["x0"])
        txt = "".join(c["text"] for c in cs)
        sizes = sorted({round(c["size"], 1) for c in cs})
        print(f"top={min(c['top'] for c in cs):6.1f} x0={cs[0]['x0']:5.1f} x1={cs[-1]['x1']:5.1f} {sizes} | {txt[:60]}")
    print("rules:", [(round(r["x0"], 1), round(r["top"], 1), round(r["x1"], 1)) for r in p.lines + p.rects if r["x1"] - r["x0"] > 200])
