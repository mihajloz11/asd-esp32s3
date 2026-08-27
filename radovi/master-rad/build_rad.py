"""Sklapa master rad u .docx prema FTN sablonu i uputstvu v8.

Format je izveden iz dva izvora, ne iz sjecanja:

* `sablon/uputstvo-za-pisanje-radova-v8.pdf` -- uputstvo nastavnika usmerenja
  za Embedded sisteme i algoritme (obavezna struktura, cirilica, kurziv za
  strane termine, tabele numerisane iznad a slike ispod, jednacine desno);
* `sablon/ftn-diplomski-sablon.doc` i `sablon/ftn-msc-rad.dot` -- zvanicni FTN
  sabloni (Heading 1 Arial 16 bold desno, Heading 2 Arial 14 bold lijevo,
  Heading 3 Arial 12 bold lijevo, Body Text Times 11 obostrano sa uvlakom
  1 cm, kod Courier New 10, potpis slike Times 11 centrirano).

Tekst se pise u `rad_tekst.py` na latinici. Ovaj modul ga po potrebi
preslovljava u cirilicu, jer uputstvo trazi cirilicu, a strani termini i kod
po istom uputstvu ostaju u izvornom latinicnom obliku.

    python build_rad.py            # oba pisma
    python build_rad.py cirilica   # samo cirilica
"""
from __future__ import annotations

import sys
from contextlib import contextmanager
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_BREAK
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Cm, Pt, RGBColor

HERE = Path(__file__).resolve().parent

BODY_FONT = "Times New Roman"
HEAD_FONT = "Arial"
CODE_FONT = "Courier New"


# --------------------------------------------------------------------------
# preslovljavanje
# --------------------------------------------------------------------------
# Digrafi idu prvi jer bi inace "nj" postalo "нј" umjesto "њ".
_DIGRAFI = [
    ("Nj", "Њ"), ("NJ", "Њ"), ("nj", "њ"),
    ("Lj", "Љ"), ("LJ", "Љ"), ("lj", "љ"),
    ("Dž", "Џ"), ("DŽ", "Џ"), ("dž", "џ"),
]
_SLOVA = {
    "A": "А", "B": "Б", "V": "В", "G": "Г", "D": "Д", "Đ": "Ђ", "E": "Е",
    "Ž": "Ж", "Z": "З", "I": "И", "J": "Ј", "K": "К", "L": "Л", "M": "М",
    "N": "Н", "O": "О", "P": "П", "R": "Р", "S": "С", "T": "Т", "Ć": "Ћ",
    "U": "У", "F": "Ф", "H": "Х", "C": "Ц", "Č": "Ч", "Š": "Ш",
    "a": "а", "b": "б", "v": "в", "g": "г", "d": "д", "đ": "ђ", "e": "е",
    "ž": "ж", "z": "з", "i": "и", "j": "ј", "k": "к", "l": "л", "m": "м",
    "n": "н", "o": "о", "p": "п", "r": "р", "s": "с", "t": "т", "ć": "ћ",
    "u": "у", "f": "ф", "h": "х", "c": "ц", "č": "ч", "š": "ш",
}


# Skracenice, oznake jedinica i imena alata ostaju u izvornom latinicnom
# obliku -- uputstvo, str. 4: "Skracenice se koriste u originalnom obliku".
# Sve sto ima cifru (ESP32-S3, I2S, INMP441) ili je citavo velikim slovima
# (AUC, PSD, DCASE) hvata pravilo, pa se ovdje nabraja samo ostatak.
_LATINICNI_TOKENI = {
    # jedinice i oznake
    "dB", "dBFS", "dBm", "Hz", "kHz", "MHz", "GHz", "s", "ms", "us", "min",
    "h", "B", "KB", "MB", "GB", "V", "mV", "mW", "W", "F", "uF", "nF",
    "pF", "cm", "mm", "m", "km", "g", "kg", "px", "dpi",
    # mjesovite skracenice koje nisu citave velikim slovima
    "pAUC", "Task", "Challenge", "Workshop", "Journal",
    # imena alata, jezika i firmi koja se u struci ne preslovljavaju
    "C", "Python", "NumPy", "SciPy", "Word", "Excel", "Windows", "Linux",
    "Android", "Git", "GitHub", "Espressif", "InvenSense", "Qualcomm",
    "Festo", "Ikotek", "Xtensa", "Welch", "Ledoit", "Wolf", "arXiv", "doi",
    "et", "al", "vol", "no", "pp", "str",
}
_LATINICNA_SLOVA = set("abcdefghijklmnopqrstuvwxyz"
                       "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
                       "čćđšžČĆĐŠŽ")
_ZNAK_TOKENA = _LATINICNA_SLOVA | set("0123456789_µΩ°")


def _ostaje_latinica(token: str) -> bool:
    if not token:
        return False
    if token in _LATINICNI_TOKENI:
        return True
    if any(z.isdigit() for z in token):          # ESP32, I2S, INMP441
        return True
    if "_" in token:                             # identifikatori iz koda
        return True
    slova = [z for z in token if z in _LATINICNA_SLOVA]
    if len(slova) >= 2 and all(z.isupper() for z in slova):
        return True                               # AUC, PSD, DCASE, UART
    return False


def u_cirilicu(tekst: str) -> str:
    """Preslovi srpski latinicni tekst u cirilicu, cuvajuci skracenice."""
    izlaz, bafer = [], []

    def isprazni():
        if not bafer:
            return
        token = "".join(bafer)
        bafer.clear()
        if _ostaje_latinica(token):
            izlaz.append(token)
            return
        for lat, cir in _DIGRAFI:
            token = token.replace(lat, cir)
        izlaz.append("".join(_SLOVA.get(z, z) for z in token))

    for znak in tekst:
        if znak in _ZNAK_TOKENA:
            bafer.append(znak)
        else:
            isprazni()
            izlaz.append(znak)
    isprazni()
    return "".join(izlaz)


# --------------------------------------------------------------------------
# inline oznake u tekstu
# --------------------------------------------------------------------------
# *strani termin*  -> kurziv, ostaje latinica (uputstvo, str. 4)
# `kod`            -> Courier New, ostaje latinica
# **naglaseno**    -> bold, preslovljava se
def _dijelovi(tekst: str):
    """Razlozi string na (tekst, stil) parove; stil je '', 'i', 'c' ili 'b'."""
    out, bafer, i = [], [], 0
    while i < len(tekst):
        if tekst.startswith("**", i):
            kraj = tekst.find("**", i + 2)
            if kraj != -1:
                out.append(("".join(bafer), ""))
                bafer = []
                out.append((tekst[i + 2:kraj], "b"))
                i = kraj + 2
                continue
        if tekst[i] == "*":
            kraj = tekst.find("*", i + 1)
            if kraj != -1:
                out.append(("".join(bafer), ""))
                bafer = []
                out.append((tekst[i + 1:kraj], "i"))
                i = kraj + 1
                continue
        if tekst[i] == "`":
            kraj = tekst.find("`", i + 1)
            if kraj != -1:
                out.append(("".join(bafer), ""))
                bafer = []
                out.append((tekst[i + 1:kraj], "c"))
                i = kraj + 1
                continue
        bafer.append(tekst[i])
        i += 1
    out.append(("".join(bafer), ""))
    return [(t, s) for t, s in out if t]


class Pisac:
    """Upisuje runove u pasus, uz izbor pisma."""

    def __init__(self, cirilica: bool):
        self.cirilica = cirilica
        self.samo_latinica = False   # engleski blokovi i literatura

    def slovi(self, tekst: str) -> str:
        if self.samo_latinica or not self.cirilica:
            return tekst
        return u_cirilicu(tekst)

    def upisi(self, pasus, tekst: str, *, bold=False, size=None, font=None,
              velika=False):
        for dio, stil in _dijelovi(tekst):
            run = pasus.add_run()
            if stil == "c":
                run.text = dio                      # kod ostaje latinica
                run.font.name = CODE_FONT
                run.font.size = Pt((size or 11) - 1)
            elif stil == "i":
                run.text = dio                      # strani termin ostaje latinica
                run.italic = True
                run.font.name = font or BODY_FONT
                run.font.size = Pt(size or 11)
            else:
                slovljeno = self.slovi(dio)
                run.text = slovljeno.upper() if velika else slovljeno
                run.bold = bold or stil == "b"
                run.font.name = font or BODY_FONT
                run.font.size = Pt(size or 11)
        return pasus


# --------------------------------------------------------------------------
# stilovi dokumenta
# --------------------------------------------------------------------------
def _podesi_stilove(doc: Document) -> None:
    normal = doc.styles["Normal"]
    normal.font.name = BODY_FONT
    normal.font.size = Pt(11)
    normal._element.rPr.rFonts.set(qn("w:eastAsia"), BODY_FONT)

    body = doc.styles["Body Text"]
    body.font.name = BODY_FONT
    body.font.size = Pt(11)
    body.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    body.paragraph_format.first_line_indent = Cm(1)
    body.paragraph_format.space_after = Pt(6)
    body.paragraph_format.line_spacing = 1.15

    for ime, velicina, poravnanje in (
        ("Heading 1", 16, WD_ALIGN_PARAGRAPH.RIGHT),
        ("Heading 2", 14, WD_ALIGN_PARAGRAPH.LEFT),
        ("Heading 3", 12, WD_ALIGN_PARAGRAPH.LEFT),
    ):
        st = doc.styles[ime]
        st.font.name = HEAD_FONT
        st.font.size = Pt(velicina)
        st.font.bold = True
        st.font.color.rgb = RGBColor(0, 0, 0)
        st.paragraph_format.alignment = poravnanje
        st.paragraph_format.space_before = Pt(18 if ime == "Heading 1" else 12)
        st.paragraph_format.space_after = Pt(10 if ime == "Heading 1" else 6)
        st.paragraph_format.keep_with_next = True

    for sekcija in doc.sections:
        sekcija.top_margin = Cm(2.5)
        sekcija.bottom_margin = Cm(2.5)
        sekcija.left_margin = Cm(3.0)
        sekcija.right_margin = Cm(2.5)


def _polje(pasus, uputstvo: str) -> None:
    """Ubaci Word polje (npr. TOC ili PAGE) u pasus."""
    r = pasus.add_run()
    poc = OxmlElement("w:fldChar")
    poc.set(qn("w:fldCharType"), "begin")
    tekst = OxmlElement("w:instrText")
    tekst.set(qn("xml:space"), "preserve")
    tekst.text = uputstvo
    razd = OxmlElement("w:fldChar")
    razd.set(qn("w:fldCharType"), "separate")
    kraj = OxmlElement("w:fldChar")
    kraj.set(qn("w:fldCharType"), "end")
    for el in (poc, tekst, razd, kraj):
        r._r.append(el)


def _broj_strane(sekcija, rimski: bool) -> None:
    stopa = sekcija.footer.paragraphs[0]
    stopa.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _polje(stopa, "PAGE \\* ROMAN" if rimski else "PAGE \\* ARABIC")


# --------------------------------------------------------------------------
# gradnja
# --------------------------------------------------------------------------
class Rad:
    def __init__(self, cirilica: bool):
        self.doc = Document()
        self.pisac = Pisac(cirilica)
        _podesi_stilove(self.doc)
        self.brojac = {"slika": 0, "tabela": 0, "listing": 0}
        self.poglavlje = 0
        self.slike: list[tuple[str, str]] = []
        self.tabele: list[tuple[str, str]] = []

    # -- osnovni blokovi ---------------------------------------------------
    @contextmanager
    def latinicno(self):
        """Blok koji se ne preslovljava (engleski tekst, literatura)."""
        prethodno = self.pisac.samo_latinica
        self.pisac.samo_latinica = True
        try:
            yield
        finally:
            self.pisac.samo_latinica = prethodno

    def prazan(self, koliko: int = 1):
        for _ in range(koliko):
            self.doc.add_paragraph()

    def nova_strana(self):
        self.doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)

    def naslov(self, tekst: str, nivo: int = 1, numerisi: bool = True):
        if nivo == 1:
            self.nova_strana()
            if numerisi:
                self.poglavlje += 1
                self.pod = 0
                self.brojac["slika"] = 0
                self.brojac["tabela"] = 0
                self.brojac["listing"] = 0
                tekst = f"{self.poglavlje}. {tekst}"
        elif nivo == 2 and numerisi:
            self.pod = getattr(self, "pod", 0) + 1
            self.podpod = 0
            tekst = f"{self.poglavlje}.{self.pod}. {tekst}"
        elif nivo == 3 and numerisi:
            self.podpod = getattr(self, "podpod", 0) + 1
            tekst = f"{self.poglavlje}.{getattr(self, 'pod', 0)}.{self.podpod}. {tekst}"
        p = self.doc.add_paragraph(style=f"Heading {nivo}")
        self.pisac.upisi(p, tekst, font=HEAD_FONT,
                         size={1: 16, 2: 14, 3: 12}[nivo], bold=True,
                         velika=(nivo == 1))
        return p

    def pasus(self, tekst: str, *, uvlaka: bool = True, centar: bool = False):
        p = self.doc.add_paragraph(style="Body Text")
        if not uvlaka:
            p.paragraph_format.first_line_indent = Cm(0)
        if centar:
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.pisac.upisi(p, tekst)
        return p

    def stavke(self, redovi: list[str]):
        for red in redovi:
            p = self.doc.add_paragraph(style="List Bullet")
            p.paragraph_format.space_after = Pt(3)
            self.pisac.upisi(p, red)

    def kod(self, tekst: str, potpis: str | None = None):
        for red in tekst.strip("\n").split("\n"):
            p = self.doc.add_paragraph()
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.left_indent = Cm(0.5)
            run = p.add_run(red if red else " ")
            run.font.name = CODE_FONT
            run.font.size = Pt(10)
        if potpis:
            self.brojac["listing"] += 1
            oznaka = f"Листинг {self.poglavlje}.{self.brojac['listing']}. " \
                if self.pisac.cirilica else \
                f"Listing {self.poglavlje}.{self.brojac['listing']}. "
            p = self.doc.add_paragraph()
            p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.space_before = Pt(6)
            self.pisac.upisi(p, oznaka + potpis, size=11)

    def referenca(self, broj: int, tekst: str):
        """Stavka literature sa visecim uvlacenjem."""
        p = self.doc.add_paragraph()
        p.paragraph_format.left_indent = Cm(0.9)
        p.paragraph_format.first_line_indent = Cm(-0.9)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        self.pisac.upisi(p, f"[{broj}] {tekst}")
        return p

    def jednacina(self, izraz: str, broj: int):
        """Jednacina lijevo, broj u malim zagradama uz desnu marginu."""
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(6)
        p.paragraph_format.space_after = Pt(6)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(7.5), WD_ALIGN_PARAGRAPH.CENTER)
        p.paragraph_format.tab_stops.add_tab_stop(Cm(15.0), WD_ALIGN_PARAGRAPH.RIGHT)
        run = p.add_run("\t" + izraz)
        run.font.name = BODY_FONT
        run.font.size = Pt(11)
        run.italic = True
        p.add_run(f"\t({broj})").font.size = Pt(11)

    # -- tabele ------------------------------------------------------------
    def tabela(self, potpis: str, zaglavlje: list[str], redovi: list[list[str]],
               desno: set[int] | None = None):
        """Tabela; po uputstvu potpis ide IZNAD tabele."""
        self.brojac["tabela"] += 1
        oznaka = f"{self.poglavlje}.{self.brojac['tabela']}"
        rijec = "Табела" if self.pisac.cirilica else "Tabela"
        p = self.doc.add_paragraph()
        p.paragraph_format.space_before = Pt(10)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        self.pisac.upisi(p, f"{rijec} {oznaka}. {potpis}")
        self.tabele.append((oznaka, potpis))

        t = self.doc.add_table(rows=1, cols=len(zaglavlje))
        t.style = "Table Grid"
        t.alignment = WD_TABLE_ALIGNMENT.CENTER
        desno = desno or set()
        for i, tekst in enumerate(zaglavlje):
            celija = t.rows[0].cells[i]
            celija.paragraphs[0].paragraph_format.space_after = Pt(2)
            celija.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            self.pisac.upisi(celija.paragraphs[0], tekst, bold=True, size=10)
        for red in redovi:
            celije = t.add_row().cells
            for i, tekst in enumerate(red):
                par = celije[i].paragraphs[0]
                par.paragraph_format.space_after = Pt(2)
                if i in desno:
                    par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
                self.pisac.upisi(par, str(tekst), size=10)
        self.doc.add_paragraph().paragraph_format.space_after = Pt(4)
        return t

    # -- slike -------------------------------------------------------------
    def slika(self, putanja: str, potpis: str, sirina_cm: float = 14.0):
        """Slika; po uputstvu potpis ide ISPOD slike."""
        self.brojac["slika"] += 1
        oznaka = f"{self.poglavlje}.{self.brojac['slika']}"
        rijec = "Слика" if self.pisac.cirilica else "Slika"
        puna = HERE / putanja
        p = self.doc.add_paragraph()
        p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_before = Pt(8)
        if puna.exists():
            p.add_run().add_picture(str(puna), width=Cm(sirina_cm))
        else:
            run = p.add_run(f"[ nedostaje slika: {putanja} ]")
            run.font.size = Pt(10)
            run.italic = True
        cap = self.doc.add_paragraph()
        cap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap.paragraph_format.space_after = Pt(10)
        self.pisac.upisi(cap, f"{rijec} {oznaka}. {potpis}")
        self.slike.append((oznaka, potpis))

    # -- naslovne strane ---------------------------------------------------
    def naslovni_blok(self, redovi: list[tuple[str, int, bool]], centar=True,
                      velika=False):
        for tekst, velicina, bold in redovi:
            p = self.doc.add_paragraph()
            p.paragraph_format.space_after = Pt(4)
            if centar:
                p.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
            p.paragraph_format.first_line_indent = Cm(0)
            if tekst:
                self.pisac.upisi(p, tekst, bold=bold, size=velicina,
                                 velika=velika)

    def kdi_tabela(self, redovi: list[tuple[str, str]]):
        t = self.doc.add_table(rows=0, cols=2)
        t.style = "Table Grid"
        for lijevo, desno in redovi:
            celije = t.add_row().cells
            celije[0].width = Cm(6.5)
            celije[1].width = Cm(9.0)
            for celija, tekst, bold in ((celije[0], lijevo, True),
                                        (celije[1], desno, False)):
                par = celija.paragraphs[0]
                par.paragraph_format.space_after = Pt(2)
                par.paragraph_format.first_line_indent = Cm(0)
                self.pisac.upisi(par, tekst, bold=bold, size=10)
        self.doc.add_paragraph()

    def sadrzaj_polje(self):
        p = self.doc.add_paragraph()
        _polje(p, r'TOC \o "1-3" \h \z \u')
        nap = self.doc.add_paragraph()
        nap.paragraph_format.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = nap.add_run(self.pisac.slovi(
            "(sadrzaj se popunjava u Wordu: desni klik na polje pa Update Field)"
        ))
        run.italic = True
        run.font.size = Pt(9)

    def snimi(self, putanja: Path):
        self.doc.save(str(putanja))
        return putanja


def main() -> int:
    import rad_tekst

    trazeno = sys.argv[1].lower() if len(sys.argv) > 1 else "oba"
    varijante = []
    if trazeno in ("oba", "cirilica"):
        varijante.append((True, "master_rad_asd_esp32s3_cir.docx"))
    if trazeno in ("oba", "latinica"):
        varijante.append((False, "master_rad_asd_esp32s3_lat.docx"))

    for cirilica, ime in varijante:
        rad = Rad(cirilica)
        rad_tekst.napisi(rad)
        put = rad.snimi(HERE / ime)
        print(f"{put.name}: {put.stat().st_size // 1024} KB, "
              f"{len(rad.slike)} slika, {len(rad.tabele)} tabela")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
