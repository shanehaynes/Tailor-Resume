"""Dev aid: pair lines of two PDFs by text prefix; print vertical/horizontal deltas."""
import sys

import pdfplumber


def lines(path):
    with pdfplumber.open(path) as pdf:
        out = {}
        for c in pdf.pages[0].chars:
            out.setdefault(round(c["top"] + 0.75 * c["size"], 1), []).append(c)
        rows = []
        for base in sorted(out):
            cs = sorted(out[base], key=lambda c: c["x0"])
            rows.append((base, cs[0]["x0"], cs[-1]["x1"], "".join(c["text"] for c in cs)))
        return rows


a, b = lines(sys.argv[1]), lines(sys.argv[2])
worst = 0.0
for (ya, xa, x1a, ta), (yb, xb, x1b, tb) in zip(a, b):
    flag = "" if ta[:25] == tb[:25] else "   TEXT DIFFERS"
    worst = max(worst, abs(ya - yb))
    print(f"dy={yb - ya:+5.1f} dx0={xb - xa:+5.1f} dx1={x1b - x1a:+5.1f} | {ta[:50]}{flag}")
print(f"lines {len(a)} vs {len(b)}; worst |dy| {worst:.1f}")
