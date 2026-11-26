"""Single source for repo paths and the pinned typst invocation."""
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TYPST = ROOT / "bin" / "typst"
FONTS = ROOT / "fonts"
LEDGER = Path(os.environ.get("RC_LEDGER", ROOT / "ledger" / "ledger.yaml"))
SCHEMA = ROOT / "ledger" / "schema.json"


def typst_compile_args(src: Path, out: Path, inputs: dict[str, str] | None = None) -> list[str]:
    """Every render goes through here so fonts and engine are always pinned."""
    extra = [a for k, v in (inputs or {}).items() for a in ("--input", f"{k}={v}")]
    return [str(TYPST), "compile", "--root", str(ROOT), "--font-path", str(FONTS),
            "--ignore-system-fonts", *extra, str(src), str(out)]


def typst_eval_args(src: Path, expr: str, inputs: dict[str, str] | None = None) -> list[str]:
    """Introspect a document (e.g. query metadata) with the same pinned engine and fonts."""
    extra = [a for k, v in (inputs or {}).items() for a in ("--input", f"{k}={v}")]
    return [str(TYPST), "eval", expr, "--in", str(src), "--root", str(ROOT), "--font-path", str(FONTS),
            "--ignore-system-fonts", *extra]
