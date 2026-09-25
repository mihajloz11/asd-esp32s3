"""Pravi PDF rada i slike strana za vizuelnu provjeru.

Na Windowsu koristi Word (isti prelom kao pri predaji), inace LibreOffice.

Pokretanje iz korijena repoa:
    python radovi/telfor2026/render_check.py [--no-render]
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
DOCX = HERE / "telfor2026_asd_esp32s3.docx"
PDF = HERE / "telfor2026_asd_esp32s3.pdf"
PREVIEW = HERE / "preview"

WD_FORMAT_PDF = 17


def word_to_pdf() -> None:
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
    print(f"Word: pages={pages} words={words}")


def soffice_to_pdf() -> None:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError("nema ni Worda ni LibreOffice-a")
    with tempfile.TemporaryDirectory(prefix="telfor-") as tmp:
        env = dict(os.environ, HOME=tmp)
        subprocess.run([soffice, "--headless", "--norestore", "--convert-to", "pdf",
                        "--outdir", tmp, str(DOCX)], check=True, env=env,
                       capture_output=True)
        shutil.copyfile(Path(tmp) / PDF.name, PDF)
    print("LibreOffice: prelom moze malo odstupati od Worda")


def render() -> None:
    try:
        import pymupdf
    except ImportError:
        print("PyMuPDF nije instaliran; preskacem slike strana")
        return
    PREVIEW.mkdir(exist_ok=True)
    doc = pymupdf.open(str(PDF))
    print(f"strana: {len(doc)}")
    for i, page in enumerate(doc, start=1):
        out = PREVIEW / f"page{i}.png"
        page.get_pixmap(dpi=110).save(str(out))
        print(f"  {out.name}")


if __name__ == "__main__":
    if sys.platform == "win32":
        word_to_pdf()
    else:
        soffice_to_pdf()
    if "--no-render" not in sys.argv:
        render()
