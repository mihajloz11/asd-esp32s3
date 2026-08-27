"""Otvori rad u Wordu, osvjezi polja (sadrzaj), prijavi broj strana i rijeci
i snimi PDF. Trazi instaliran MS Word.

    ..\\..\\.venv\\Scripts\\python.exe render_check.py [ime.docx]
"""
from __future__ import annotations

import sys
from pathlib import Path

import win32com.client as win32

HERE = Path(__file__).resolve().parent
PODRAZUMIJEVANI = "master_rad_asd_esp32s3_cir.docx"

WD_STAT_PAGES = 2
WD_STAT_WORDS = 0


def main() -> int:
    ime = sys.argv[1] if len(sys.argv) > 1 else PODRAZUMIJEVANI
    docx = HERE / ime
    if not docx.exists():
        print(f"nema {docx}")
        return 1

    word = win32.DispatchEx("Word.Application")
    word.Visible = False
    word.DisplayAlerts = False
    try:
        doc = word.Documents.Open(str(docx))
        # Polja se osvjezavaju dva puta: prvo se popuni sadrzaj, pa se poslije
        # njegovog preloma poravnaju brojevi strana.
        for _ in range(2):
            doc.Fields.Update()
            for toc in doc.TablesOfContents:
                toc.Update()
        doc.Save()
        strana = doc.ComputeStatistics(WD_STAT_PAGES)
        rijeci = doc.ComputeStatistics(WD_STAT_WORDS)
        pdf = docx.with_suffix(".pdf")
        doc.SaveAs2(str(pdf), FileFormat=17)
        doc.Close(False)
    finally:
        word.Quit()

    print(f"{docx.name}: strana={strana} rijeci={rijeci}")
    print(f"pdf: {pdf.name} ({pdf.stat().st_size // 1024} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
