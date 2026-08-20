"""Konvertuje rad u PDF preko Worda i renderuje strane u slike za provjeru.

Pokretanje:
    ..\\..\\.venv\\Scripts\\python.exe render_check.py
"""

from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCX = HERE / "telfor2026_asd_esp32s3.docx"
PDF = HERE / "telfor2026_asd_esp32s3.pdf"
PREVIEW = HERE / "preview"

WD_FORMAT_PDF = 17


def to_pdf() -> Path:
    import win32com.client as win32

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    try:
        doc = word.Documents.Open(str(DOCX), ReadOnly=False)
        doc.Repaginate()
        pages = doc.ComputeStatistics(2)  # wdStatisticPages
        words = doc.ComputeStatistics(0)  # wdStatisticWords
        doc.SaveAs(str(PDF), FileFormat=WD_FORMAT_PDF)
        doc.Close(SaveChanges=0)
    finally:
        word.Quit()
    print(f"pages={pages} words={words}")
    return PDF


def render(pdf: Path) -> None:
    try:
        import fitz
    except ImportError:
        print("PyMuPDF nije instaliran; preskacem renderovanje slika")
        return
    PREVIEW.mkdir(exist_ok=True)
    doc = fitz.open(str(pdf))
    for i, page in enumerate(doc, start=1):
        pix = page.get_pixmap(dpi=110)
        out = PREVIEW / f"page{i}.png"
        pix.save(str(out))
        print(f"  {out.name}")


if __name__ == "__main__":
    pdf = to_pdf()
    if "--no-render" not in sys.argv:
        render(pdf)
