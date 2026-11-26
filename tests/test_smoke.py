import subprocess

from rc.paths import FONTS, ROOT, TYPST, typst_compile_args

EXPECTED = "Workflow office fiscal efficient affiliate. Streamlined workflows reflect financial findings."


def test_pinned_typst_version():
    want = (ROOT / ".typst-version").read_text().strip()
    out = subprocess.run([str(TYPST), "--version"], capture_output=True, text=True, check=True).stdout
    assert out.startswith(f"typst {want} "), out


def test_fonts_committed():
    names = {p.name for p in FONTS.glob("*.ttf")}
    assert {"Carlito-Regular.ttf", "Carlito-Bold.ttf", "Carlito-Italic.ttf", "Carlito-BoldItalic.ttf"} <= names


def test_render_text_layer_is_ats_clean(tmp_path):
    pdf = tmp_path / "smoke.pdf"
    subprocess.run(typst_compile_args(ROOT / "tests/smoke/smoke.typ", pdf), check=True)
    fonts = subprocess.run(["pdffonts", str(pdf)], capture_output=True, text=True, check=True).stdout
    assert "Carlito" in fonts, fonts
    text = subprocess.run(["pdftotext", "-raw", str(pdf), "-"], capture_output=True, text=True, check=True).stdout
    flat = " ".join(text.split())
    assert EXPECTED in flat, flat
    assert not any(c in flat for c in "\ufb00\ufb01\ufb02\ufb03\ufb04\ufffd"), "ligature or replacement glyph in text layer"
