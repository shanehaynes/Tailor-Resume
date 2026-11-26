"""Render a resolved resume to PDF with the pinned engine and fonts."""
import subprocess
from pathlib import Path

from rc.paths import ROOT, typst_compile_args

TEMPLATE = ROOT / "templates" / "resume.typ"


def render(resolved: Path, out: Path) -> Path:
    """resolved must live under the repo root (Typst's --root sandbox)."""
    rel = "/" + Path(resolved).resolve().relative_to(ROOT).as_posix()
    out.parent.mkdir(parents=True, exist_ok=True)
    r = subprocess.run(typst_compile_args(TEMPLATE, out, {"resolved": rel}), capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError(f"typst failed:\n{r.stderr}")
    return out
