"""Snimi izabrane strane rada kao PNG, da se prelom moze vizuelno provjeriti.

Radi preko Worda: eksportuje trazeni opseg strana u zaseban PDF, pa taj PDF
renderuje kroz PyMuPDF ako je dostupan, a u suprotnom kroz Word-ov izvoz slika
stranica.

    ..\\..\\.venv\\Scripts\\python.exe preview_strane.py 1 2 3 12
"""
from __future__ import annotations

import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
OUT = HERE / "preview"
OUT.mkdir(exist_ok=True)


def main() -> int:
    strane = [int(a) for a in sys.argv[1:]] or [1, 2, 3]
    pdf = HERE / "master_rad_asd_esp32s3_cir.pdf"
    if not pdf.exists():
        print("prvo pokreni render_check.py")
        return 1
    try:
        import fitz  # PyMuPDF
    except ImportError:
        print("nema PyMuPDF; instaliraj sa: pip install pymupdf")
        return 1

    dok = fitz.open(str(pdf))
    for br in strane:
        if br < 1 or br > dok.page_count:
            print(f"  strana {br} ne postoji (ukupno {dok.page_count})")
            continue
        piks = dok[br - 1].get_pixmap(dpi=110)
        put = OUT / f"strana{br:02d}.png"
        piks.save(str(put))
        print("  ", put.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
