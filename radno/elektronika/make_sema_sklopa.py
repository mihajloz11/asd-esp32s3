#!/usr/bin/env python3
"""Generiše šemu sklopa ASD — DVIJE ODVOJENE PLOČE.

  PLOČA U (uređaj)  — ESP32-S3 + INMP441 + taster + 2 LED + 2 otpornika.
                      Radi sama, napaja se iz powerbanka preko USB-C.
  PLOČA M (mjerna)  — AMS1117 + INA226 + 470 µF + ulaz za 5 V.
                      Kači se na ploču U preko 4 žice, samo za E5 mjerenje
                      potrošnje, i poslije mjerenja se skida.

Izvori istine:
  - firmware/esp32s3_asd/main/pins.h        (GPIO mapa)
  - radno/elektronika/plan-dvije-plocice.md (podjela komponenti + tačna topologija
                                             INA226: VCC prije šanta, VBS na IN−)
  - radno/elektronika/sema-povezivanja.md   (pinout INMP441, rizik C7)
  - radno/elektronika/img/inmp441-2.jpg     (okrugli modul 12,0 x 14,0 mm, 2x3 pada)
  - radno/elektronika/img/ina226.jpeg       (20,5 x 19,4 mm, 1x8, jedan R100)
  - radno/elektronika/img/ams1117.webp      (plavi modul, 2+2 pina)
  - Espressif ESP32-S3-DevKitC-1 v1.1 user guide (J1/J3 tabele)

Izlaz: sema-sklopa.pdf (7 strana A4) + img/sema-sklopa-s{1..7}.png
  (pored samog skripta — putanje se računaju iz Path(__file__).parent)
  1  podjela na dvije ploče + interfejs od 4 žice
  2  ploča U — logička šema
  3  ploča U — fizički raspored, uvećano
  4  ploča M — logička šema + fizički raspored
  5  obje ploče u razmjeri 1:1, za štampu
  6  tabele veza (U, interfejs, M)
  7  spisak komponenti po pločama + kartice modula
"""
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Circle, FancyBboxPatch, Rectangle, Wedge

DOCS = Path(__file__).resolve().parent
IMG = DOCS / "img"

A4W, A4H = 297.0, 210.0  # landscape, mm
PITCH = 2.54

C_BG = "#ffffff"
C_INK = "#1a1a1a"
C_MUTED = "#6b7280"
C_PCB = "#2e7d4f"          # ploča U — zelena
C_PCB2 = "#1f4e79"         # ploča M — plava, da se odmah razlikuju
C_PAD = "#d9c07a"
C_RED = "#d62828"
C_BLACK = "#111111"
C_YEL = "#e8a33d"
C_GRN = "#2e9e4f"
C_BLU = "#2f6fd0"
C_WHT = "#9aa3ad"
C_VIO = "#7b3fbf"
C_GRY = "#8a8a8a"
C_ORA = "#e2711d"
C_WARN = "#b3261e"

# dva 3,3 V čvora na mjernoj ploči — NIKAD spojena, između njih je shunt
C_SRC = "#e2711d"          # 3V3 IZVOR   (AMS1117 OUT+ → INA226 IN+ / VCC)
C_LOAD = "#c026d3"         # 3V3 POTROŠAČ (INA226 IN− → 470 µF → ploča U)

# bijela podloga za tekst koji pada na obojenu ploču
BB = dict(boxstyle="square,pad=0.15", fc="white", ec="none", alpha=0.88)

# Espressif DevKitC-1 v1.1, header blokovi (pin 1 -> pin 22)
J1 = ["3V3", "3V3", "RST", "4", "5", "6", "7", "15", "16", "17", "18",
      "8", "3", "46", "9", "10", "11", "12", "13", "14", "5V", "G"]
J3 = ["G", "TX", "RX", "1", "2", "42", "41", "40", "39", "38", "37",
      "36", "35", "0", "45", "48", "47", "21", "20", "19", "G", "G"]

# GPIO -> (boja žice, kratka oznaka) — samo pinovi koji se koriste
USED_J1 = {"4": (C_YEL, "SCK"), "5": (C_GRN, "WS"), "6": (C_BLU, "SD"),
           "8": (C_WHT, "SDA"), "9": (C_VIO, "SCL"), "10": (C_GRY, "TASTER"),
           "11": (C_ORA, "LED crv.")}

INA_PINS = [("IN+", C_SRC), ("IN−", C_LOAD), ("VBS", C_LOAD), ("ALE", "#4b5563"),
            ("SDA", C_WHT), ("SCL", C_VIO), ("GND", C_BLACK), ("VCC", C_SRC)]

# konektori na ploči U
K_MIC = [("VDD", C_RED), ("GND", C_BLACK), ("SCK", C_YEL),
         ("WS", C_GRN), ("SD", C_BLU), ("L/R", C_BLACK)]
K_BTN = [("GPIO10", C_GRY), ("GND", C_BLACK)]
K_M = [("3V3", C_LOAD), ("GND", C_BLACK), ("SDA", C_WHT), ("SCL", C_VIO)]
K_UART = [("TX", "#0ea5e9"), ("RX", "#84cc16"), ("GND", C_BLACK)]

# ---------------------------------------------------------------- tabele veza
# (od, do, boja žice, ime boje, napomena)
NETS_U = [
    ("S3  3V3  (J1-1)", "3V3 šina ploče U", C_RED, "crvena", "šinu hrani ILI USB ILI ploča M"),
    ("S3  3V3  (J1-2)", "3V3 šina ploče U", C_RED, "crvena", "isti čvor, drugi pin"),
    ("S3  GND  (J1-22)", "GND šina ploče U", C_BLACK, "crna", "zvjezdasta masa"),
    ("S3  GND  (J3-1)", "GND šina ploče U", C_BLACK, "crna", "drugi pin mase"),
    ("K-MIK  pin 1  VDD", "3V3 šina", C_RED, "crvena", "napajanje mikrofona"),
    ("K-MIK  pin 2  GND", "GND šina", C_BLACK, "crna", "masa"),
    ("K-MIK  pin 3  SCK", "S3  GPIO4  (J1-4)", C_YEL, "žuta", "I2S bit clock"),
    ("K-MIK  pin 4  WS", "S3  GPIO5  (J1-5)", C_GRN, "zelena", "I2S word select"),
    ("K-MIK  pin 5  SD", "S3  GPIO6  (J1-6)", C_BLU, "plava", "I2S podaci → S3"),
    ("K-MIK  pin 6  L/R", "GND šina", C_BLACK, "crna", "LIJEVI KANAL — obavezno!"),
    ("S3  GPIO2  (J3-5)", "330 Ω → zelena LED → GND", C_GRN, "zelena", "status, pet obrazaca"),
    ("S3  GPIO11 (J1-17)", "330 Ω → crvena LED → GND", C_ORA, "narandž.", "alarm"),
    ("K-TAS  pin 1", "S3  GPIO10  (J1-16)", C_GRY, "siva", "interni pull-up, bez otpornika"),
    ("K-TAS  pin 2", "GND šina", C_BLACK, "crna", "drugi jezičak tastera"),
    ("K-M  pin 1  3V3", "3V3 šina", C_LOAD, "ljubičasta", "ulaz 3,3 V sa ploče M"),
    ("K-M  pin 2  GND", "GND šina", C_BLACK, "crna", "zajednička masa sa pločom M"),
    ("K-M  pin 3  SDA", "S3  GPIO8  (J1-12)", C_WHT, "bijela", "I2C ka INA226 (0x44)"),
    ("K-M  pin 4  SCL", "S3  GPIO9  (J1-15)", C_VIO, "ljubičasta", "I2C ka INA226"),
    ("K-UART  pin 1  TX", "S3  TX  (J3-2, GPIO43)", "#0ea5e9", "svijetloplava", "→ RX na USB-TTL adapteru"),
    ("K-UART  pin 2  RX", "S3  RX  (J3-3, GPIO44)", "#84cc16", "svijetlozelena", "← TX na USB-TTL adapteru"),
    ("K-UART  pin 3  GND", "GND šina", C_BLACK, "crna", "zajednička masa sa adapterom"),
]

NETS_M = [
    ("5 V ULAZ  +", "AMS1117  IN+", C_RED, "crvena", "zidni punjač, ne powerbank"),
    ("5 V ULAZ  −", "GND šina ploče M", C_BLACK, "crna", "zajednička masa"),
    ("AMS1117  IN−", "GND šina ploče M", C_BLACK, "crna", "masa regulatora"),
    ("AMS1117  OUT+", "INA226  IN+", C_SRC, "narandž.", "čvor 3V3 IZVOR"),
    ("AMS1117  OUT−", "GND šina ploče M", C_BLACK, "crna", "masa regulatora"),
    ("INA226  VCC", "čvor 3V3 IZVOR", C_SRC, "narandž.", "prije shunta — ne mjeri sam sebe"),
    ("INA226  GND", "GND šina ploče M", C_BLACK, "crna", "masa senzora"),
    ("INA226  IN−", "čvor 3V3 POTROŠAČ", C_LOAD, "ljubičasta", "shunt U SERIJI — ovdje izlazi struja"),
    ("INA226  SDA", "K-U  pin 3", C_WHT, "bijela", "pull-up je već na modulu"),
    ("INA226  SCL", "K-U  pin 4", C_VIO, "ljubičasta", "I2C"),
    ("INA226  VBS", "čvor 3V3 POTROŠAČ", C_LOAD, "ljubičasta", "OBAVEZNO — bez toga power = 0"),
    ("INA226  ALE", "— nepovezan —", None, "—", "ostaviti prazno"),
    ("470 µF  (+)", "čvor 3V3 POTROŠAČ", C_LOAD, "ljubičasta", "vadiv, samo ako brownout"),
    ("470 µF  (−)", "GND šina ploče M", C_BLACK, "crna", "polarizovan!"),
    ("K-U  pin 1  3V3", "čvor 3V3 POTROŠAČ", C_LOAD, "ljubičasta", "izlaz ka ploči U"),
    ("K-U  pin 2  GND", "GND šina ploče M", C_BLACK, "crna", "masa ka ploči U"),
]

NETS_IF = [
    ("M  K-U pin 1  3V3", "U  K-M pin 1  3V3", C_LOAD, "ljubičasta",
     "napaja cijelu ploču U; USB mora biti otkačen"),
    ("M  K-U pin 2  GND", "U  K-M pin 2  GND", C_BLACK, "crna",
     "zajednička masa — obavezno, inače I2C ne radi"),
    ("M  K-U pin 3  SDA", "U  K-M pin 3  SDA", C_WHT, "bijela", "GPIO8"),
    ("M  K-U pin 4  SCL", "U  K-M pin 4  SCL", C_VIO, "ljubičasta", "GPIO9"),
]

# ---------------------------------------------------------- spisak komponenti
BOM_U = [
    ("ESP32-S3-DevKitC-1 N32R16V", "1", "63,0 × 25,5 mm, 2×22 pina", "imaš"),
    ("Muška letvica 40 pin  (A1632)", "2", "2,54 mm — ~44 pina na S3", "imaš"),
    ("PIN letvica 40x1 prava F", "3", "ženska 2,54 mm · MP 407 · reže se", "KUPITI 3×42 din"),
    ("Test ploča 100x50 tačke", "1", "18 × 38 rupa · Mikro Princ 057516", "KUPITI 144 din"),
    ("LED 5 mm zelena  (A3506)", "1", "prozirna — status", "imaš"),
    ("LED 5 mm crvena  (A2177)", "1", "alarm", "imaš"),
    ("RM1/4 330 otpornik", "10", "metal film 0,25 W ±1 % · MP 32004 (min 10)", "KUPITI 23 din"),
    ("  → 2 × 1×22 za S3", "44", "kolone 3 i 12, redovi 4–25", "iz letvice"),
    ("  → K-MIK 1×6 i K-TAS 1×2", "8", "kolona 16, redovi 3–8 i 12–13", "iz letvice"),
    ("  → K-M 1×4", "4", "kolona 16, redovi 17–20", "iz letvice"),
    ("  → K-UART 1×3", "3", "kolona 16, redovi 24–26 — TX/RX/GND", "iz letvice"),
    ("Gola kalajisana žica", "≈15 cm", "GND i 3V3 šina", "imaš"),
]

BOM_U_OFF = [
    ("INMP441  (A1477)", "1", "12,0 × 14,0 mm, na žicama < 10 cm", "imaš, +1 rezerva"),
    ("CKM 0.1uF/63V RM2.5", "1", "keramika 100 nF, raster 2,54 — NA PADOVE MIKROFONA", "KUPITI 12 din"),
    ("Elektrolit 10 µF  (iz A642K)", "1", "polarizovan — NA PADOVE MIKROFONA", "imaš"),
    ("Arkadni taster 30 mm  (A4059)", "1", "2 faston jezička 2,8 mm, plavi", "imaš"),
    ("Powerbank + USB-C kabl", "1", "napajanje u normalnom radu", "imaš"),
]

BOM_M = [
    ("Prototipna ploča 4×6 cm  (A1938)", "1", "15 × 23 rupe — ovo je ploča M", "imaš"),
    ("AMS1117-3.3 modul 800 mA  (A1652)", "1", "≈20 × 10 mm, 4 muška pina već zalemljena", "imaš"),
    ("INA226 modul  (A3627)", "1", "20,5 × 19,4 mm, R100 = 0,1 Ω, adresa 0x44", "imaš"),
    ("Elektrolit 470 µF  (iz A642K)", "1", "polarizovan, na VADIVIM kontaktima", "imaš"),
    ("Ženski header 1×8  (INA226)", "8", "red 18 — modul ostaje vadiv", "iz letvice"),
    ("Ženski header 2× 1×2 (AMS1117)", "4", "red 6 — OUT kol. 4–5, IN kol. 10–11", "iz letvice"),
    ("Ženski header 1×2  (470 µF)", "2", "red 20, kolone 13–14 — vadiv", "iz letvice"),
    ("Ženski header 1×2  (5 V ULAZ)", "2", "kolona 14, redovi 3–4", "iz letvice"),
    ("Ženski header 1×4  (K-U)", "4", "kolona 2, redovi 17–20", "iz letvice"),
    ("Gola kalajisana žica", "≈10 cm", "GND šina", "imaš"),
]

BOM_M_OFF = [
    ("Zidni punjač 5 V", "1", "presječen USB kabl: crvena = +5 V, crna = GND", "imaš"),
    ("Kabl 4 žile, ≈20 cm", "1", "K-U (ploča M) ↔ K-M (ploča U)", "imaš jumpere"),
]


# ------------------------------------------------------------------ pomoćne
def new_page(pdf, title, subtitle):
    fig = plt.figure(figsize=(A4W / 25.4, A4H / 25.4), dpi=300)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, A4W)
    ax.set_ylim(0, A4H)
    ax.invert_yaxis()
    ax.axis("off")
    ax.set_facecolor(C_BG)
    ax.text(14, 13, title, fontsize=15, fontweight="bold", color=C_INK, va="center")
    ax.text(14, 20.5, subtitle, fontsize=8, color=C_MUTED, va="center")
    ax.plot([14, A4W - 14], [25, 25], color="#d4d4d8", lw=0.8)
    return fig, ax


def footer(ax, txt, right="mjerilo 1:1  ·  raster 2,54 mm"):
    ax.text(14, A4H - 8, txt, fontsize=6, color=C_MUTED, va="center")
    ax.text(A4W - 14, A4H - 8, right, fontsize=6, color=C_MUTED, va="center", ha="right")


def chip(ax, x, y, w, h, label, fc, ec, fs=7):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=fc, ec=ec, lw=0.9, zorder=3))
    if label:
        ax.text(x + w / 2, y + h / 2, label, fontsize=fs, ha="center", va="center",
                color="white", fontweight="bold", zorder=4)


def panel(ax, x, y, w, h, title, lines, fc="#f8fafc", ec="#cbd5e1", tc=None, fs=5.3, lh=5.2):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2",
                                fc=fc, ec=ec, lw=0.85, zorder=1))
    ax.text(x + 5, y + 7, title, fontsize=7.5, color=tc or C_INK, fontweight="bold",
            zorder=2)
    for i, t in enumerate(lines):
        ax.text(x + 5, y + 14 + i * lh, t, fontsize=fs, color=C_INK, zorder=2)


def save(pdf, fig, n):
    pdf.savefig(fig)
    fig.savefig(IMG / f"sema-sklopa-s{n}.png", dpi=170)
    plt.close(fig)


# ============================================================ STRANA 1
def page_overview(pdf):
    fig, ax = new_page(
        pdf, "Podjela na dvije ploče",
        "PLOČA U radi sama iz powerbanka.  Mjerni dio se kači na nju sa 4 žice samo za "
        "E5, pa se skida — i ne mora biti zalemljen (varijanta A, dolje desno).")

    # ---------------- PLOČA U
    ux, uy, uw, uh = 16, 34, 112, 112
    ax.add_patch(FancyBboxPatch((ux, uy), uw, uh, boxstyle="round,pad=0,rounding_size=3",
                                fc="#f1f8f3", ec=C_PCB, lw=1.6))
    ax.text(ux + 6, uy + 9, "PLOČA U — UREĐAJ", fontsize=10.5, color=C_PCB,
            fontweight="bold")
    ax.text(ux + 6, uy + 15.5, "prototipna ploča 100 × 50 mm  ·  ostaje zalemljena zauvijek",
            fontsize=6, color=C_MUTED)

    chip(ax, ux + 8, uy + 21, 58, 26, "", "#1f2937", "#111827")
    ax.text(ux + 37, uy + 30, "ESP32-S3-DevKitC-1", fontsize=7.5, ha="center",
            color="white", fontweight="bold", zorder=5)
    ax.text(ux + 37, uy + 36, "N32R16V  ·  na ženskim headerima (vadiv)",
            fontsize=5, ha="center", color="#9ca3af", zorder=5)
    ax.text(ux + 37, uy + 42, "napajanje: USB-C ← powerbank", fontsize=5,
            ha="center", color="#9ca3af", zorder=5)

    for i, (t, sub, col) in enumerate([
            ("2 LED + 2 × 330 Ω", "GPIO2 zelena · GPIO11 crvena", C_GRN),
            ("K-MIK  1×6", "ženski header → INMP441 na žicama", C_BLU),
            ("K-TAS 1×2  ·  K-UART 1×3", "taster  ·  TX/RX/GND za USB-TTL", C_GRY),
            ("GND + 3V3 šina", "gola kalajisana žica, donji rub ploče", C_RED)]):
        yy = uy + 53 + i * 13
        ax.add_patch(FancyBboxPatch((ux + 8, yy), 58, 10,
                                    boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="white", ec=col, lw=0.8))
        ax.text(ux + 11, yy + 4, t, fontsize=6, color=C_INK, fontweight="bold")
        ax.text(ux + 11, yy + 8, sub, fontsize=4.8, color=C_MUTED)

    ax.add_patch(FancyBboxPatch((ux + 72, uy + 53), 34, 36,
                                boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#ede9fe", ec=C_LOAD, lw=1.1))
    ax.text(ux + 89, uy + 60, "K-M  1×4", fontsize=7, ha="center", color=C_LOAD,
            fontweight="bold")
    ax.text(ux + 89, uy + 66, "spoj sa mjernim\nsklopom", fontsize=5,
            ha="center", color=C_INK, linespacing=1.4)
    ax.text(ux + 89, uy + 78, "3V3 · GND · SDA · SCL", fontsize=5, ha="center",
            color=C_MUTED)
    ax.text(ux + 89, uy + 84, "prazan kad se ne mjeri", fontsize=4.8, ha="center",
            color=C_MUTED, style="italic")

    # ---------------- PLOČA M
    mx, my, mw, mh = 168, 34, 112, 112
    ax.add_patch(FancyBboxPatch((mx, my), mw, mh, boxstyle="round,pad=0,rounding_size=3",
                                fc="#eff6ff", ec=C_PCB2, lw=1.6))
    ax.text(mx + 6, my + 9, "PLOČA M — MJERNA", fontsize=10.5, color=C_PCB2,
            fontweight="bold")
    ax.text(mx + 6, my + 15.5, "ploča 4 × 6 cm (A1938) ILI MB-102  ·  kači se samo za E5",
            fontsize=6, color=C_MUTED)

    for i, (t, sub, col) in enumerate([
            ("5 V ULAZ  1×2", "5 V sa punjača — otpada uz lab. napajanje", C_RED),
            ("AMS1117-3.3  modul", "5 V → 3,3 V — otpada uz lab. napajanje", C_BLU),
            ("INA226  modul", "shunt R100 = 0,1 Ω U SERIJI · I2C 0x44", C_PCB2),
            ("470 µF elektrolit", "VADIV — ubada se samo ako se javi brownout", C_ORA),
            ("GND šina", "gola kalajisana žica, donji rub", C_BLACK)]):
        yy = my + 22 + i * 13
        ax.add_patch(FancyBboxPatch((mx + 8, yy), 62, 10,
                                    boxstyle="round,pad=0,rounding_size=1.2",
                                    fc="white", ec=col, lw=0.8))
        ax.text(mx + 11, yy + 4, t, fontsize=6, color=C_INK, fontweight="bold")
        ax.text(mx + 11, yy + 8, sub, fontsize=4.8, color=C_MUTED)

    ax.add_patch(FancyBboxPatch((mx + 76, my + 22), 30, 36,
                                boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#ede9fe", ec=C_LOAD, lw=1.1))
    ax.text(mx + 91, my + 29, "K-U  1×4", fontsize=7, ha="center", color=C_LOAD,
            fontweight="bold")
    ax.text(mx + 91, my + 36, "izlaz ka\nuređaju", fontsize=5, ha="center",
            color=C_INK, linespacing=1.4)
    ax.text(mx + 91, my + 47, "3V3 · GND\nSDA · SCL", fontsize=5, ha="center",
            color=C_MUTED, linespacing=1.4)

    ax.text(mx + 91, my + 68, "Zašto odvojeno:", fontsize=6, ha="center", color=C_INK,
            fontweight="bold")
    ax.text(mx + 91, my + 76, "mjeri se jednom,\ntraži otkačen USB,\nrasklapa se.",
            fontsize=5, ha="center", color=C_MUTED, linespacing=1.5)
    ax.text(mx + 91, my + 92, "Zato i ne mora biti\nzalemljen — isti sklop\nradi i na MB-102.",
            fontsize=5, ha="center", color=C_WARN, linespacing=1.5, style="italic")

    # ---------------- interfejs 4 žice
    ix0, ix1 = ux + uw, mx
    for i, (nm, col) in enumerate(K_M):
        yy = 74 + i * 9
        ax.plot([ix0, ix1], [yy, yy], color=col, lw=2.0, solid_capstyle="round")
        ax.add_patch(Circle((ix0, yy), 1.1, fc=col, ec="none", zorder=3))
        ax.add_patch(Circle((ix1, yy), 1.1, fc=col, ec="none", zorder=3))
        ax.text((ix0 + ix1) / 2, yy - 2.4, nm, fontsize=5.6, ha="center",
                color=C_INK, fontweight="bold", zorder=4, bbox=BB)
    ax.text((ix0 + ix1) / 2, 62, "4 žice", fontsize=8, ha="center", color=C_INK,
            fontweight="bold")
    ax.text((ix0 + ix1) / 2, 68, "≈ 20 cm", fontsize=5.5, ha="center", color=C_MUTED)
    ax.annotate("", xy=(ix1 - 2, 116), xytext=(ix0 + 2, 116),
                arrowprops=dict(arrowstyle="<->", color=C_MUTED, lw=0.9))
    ax.text((ix0 + ix1) / 2, 122, "skida se\nposlije mjerenja", fontsize=5,
            ha="center", color=C_MUTED, linespacing=1.4)

    # ---------------- van ploča
    ax.text(ux, 156, "Van ploče U — na žicama", fontsize=7.5, color=C_INK,
            fontweight="bold")
    for i, (t, sub) in enumerate([
            ("INMP441 mikrofon", "žice < 10 cm, usmjeren ka ventilatoru"),
            ("100 nF + 10 µF", "leme se NA PADOVE MIKROFONA, ne na ploču"),
            ("Arkadni taster 30 mm", "2 faston jezička — žica se nabija"),
            ("Powerbank + USB-C", "napajanje u normalnom radu")]):
        yy = 164 + i * 8
        ax.add_patch(Circle((ux + 2, yy - 1.6), 1.0, fc=C_PCB, ec="none"))
        ax.text(ux + 6, yy, t, fontsize=6, color=C_INK, fontweight="bold")
        ax.text(ux + 6, yy + 4, sub, fontsize=5, color=C_MUTED)

    panel(ax, 132, 150, 148, 20,
          "PRAVILO KOJE SE NE KRŠI",
          ["ILI powerbank preko USB-C  ILI  mjerni sklop preko K-M/3V3.  NIKAD oboje.",
           "Redoslijed za E5: otkači USB → ubodi 4-žilni kabl → tek onda uključi napajanje."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.4, lh=5.4)

    panel(ax, 132, 174, 148, 22,
          "VARIJANTA A — laboratorijsko napajanje (preporučeno)",
          ["Lab. napajanje da 3,3 V pravo na INA226 IN+ → AMS1117 i 5 V ULAZ otpadaju.",
           "Ostaju INA226 + 470 µF + 4 žice — to staje na MB-102, bez lemljenja ploče M."],
          fc="#f0f7ff", ec="#7ba7d7", tc="#1e5aa8", fs=5.4, lh=5.4)

    footer(ax, "Strana 1/7 — podjela.  Detaljne veze: strane 2–4, tabele: strane 6–7.", "")
    save(pdf, fig, 1)


# ============================================================ STRANA 2
def page_schema_u(pdf):
    fig, ax = new_page(
        pdf, "PLOČA U (uređaj) — logička šema",
        "ESP32-S3-WROOM-1 N32R16V  ·  INMP441  ·  taster  ·  2 LED   |   "
        "pinovi iz firmware/esp32s3_asd/main/pins.h")

    bx, by, bw, bh = 118, 40, 60, 110
    chip(ax, bx, by, bw, bh, "", "#1f2937", "#111827")
    ax.text(bx + bw / 2, by + 8, "ESP32-S3-DevKitC-1", fontsize=8.5, ha="center",
            color="white", fontweight="bold")
    ax.text(bx + bw / 2, by + 13.5, "ESP32-S3-WROOM-1  N32R16V", fontsize=6, ha="center",
            color="#9ca3af")
    ax.text(bx + bw / 2, by + 18, "32 MB flash · 16 MB oktalni PSRAM", fontsize=5.5,
            ha="center", color="#9ca3af")
    ax.text(bx + bw / 2, by + bh - 5, "USB-C  ←  powerbank", fontsize=6,
            ha="center", color="#9ca3af", fontweight="bold")

    left = [("3V3", "J1-1", C_RED), ("3V3", "J1-2", C_ORA), ("GPIO4", "J1-4", C_YEL),
            ("GPIO5", "J1-5", C_GRN), ("GPIO6", "J1-6", C_BLU), ("GPIO8", "J1-12", C_WHT),
            ("GPIO9", "J1-15", C_VIO), ("GPIO10", "J1-16", C_GRY),
            ("GPIO11", "J1-17", C_ORA), ("GND", "J1-22", C_BLACK)]
    y0, dy = by + 24, 8.4
    lp = {}
    for i, (nm, hp, col) in enumerate(left):
        yy = y0 + i * dy
        ax.plot([bx - 4, bx], [yy, yy], color=col, lw=1.6, solid_capstyle="round", zorder=2)
        ax.add_patch(Circle((bx - 4, yy), 0.9, fc=col, ec="none", zorder=3))
        ax.text(bx + 2.5, yy, nm, fontsize=6.5, va="center", color="white",
                fontweight="bold")
        ax.text(bx + 22, yy, hp, fontsize=5.5, va="center", color="#9ca3af")
        lp[hp if nm == "3V3" else nm] = (bx - 4, yy)

    yg2 = by + 26
    ax.plot([bx + bw, bx + bw + 4], [yg2, yg2], color=C_GRN, lw=1.6,
            solid_capstyle="round", zorder=2)
    ax.add_patch(Circle((bx + bw + 4, yg2), 0.9, fc=C_GRN, ec="none", zorder=3))
    ax.text(bx + bw - 2.5, yg2, "GPIO2  (J3-5)", fontsize=6.5, va="center", ha="right",
            color="white", fontweight="bold")
    lp["GPIO2"] = (bx + bw + 4, yg2)

    ax.text(bx + bw / 2, by + bh + 5,
            "GPIO 35/36/37 zauzeti oktalnim PSRAM-om — ne koristiti.\n"
            "Strapping 0/3/45/46 izbjegavati.",
            fontsize=5.5, ha="center", color=C_WARN, linespacing=1.5)

    # ---- INMP441 (van ploče)
    mx, my = 38, 40
    ax.add_patch(Circle((mx + 13, my + 13), 13, fc="#141414", ec="#3f3f46", lw=0.9, zorder=3))
    for a in (35, 125, 215, 305):
        ax.add_patch(Wedge((mx + 13, my + 13), 13, a - 16, a + 16, width=2.6,
                           fc=C_PAD, ec="none", zorder=4))
    ax.add_patch(Rectangle((mx + 9.6, my + 9.6), 6.8, 6.8, fc="#c8ccd2",
                           ec="#8b8f96", lw=0.6, zorder=5))
    ax.text(mx + 13, my + 13, "441", fontsize=5, ha="center", va="center",
            color="#3f3f46", zorder=6)
    ax.text(mx + 13, my - 5, "INMP441  —  VAN PLOČE", fontsize=8, ha="center",
            color=C_INK, fontweight="bold")
    ax.text(mx + 13, my + 31, "12,0 × 14,0 mm  ·  6 pada u 2 reda po 3",
            fontsize=5.5, ha="center", color=C_MUTED)
    ax.text(mx + 13, my + 35.5, "na žicama < 10 cm, usmjeren ka ventilatoru",
            fontsize=5.5, ha="center", color=C_MUTED, style="italic")

    mic_y = {}
    for i, (nm, col) in enumerate(K_MIC):
        yy = my + 46 + i * 9.0
        mic_y[nm] = yy
        ax.add_patch(Circle((mx + 13, yy), 1.0, fc=col, ec="#3f3f46", lw=0.4, zorder=4))
        ax.text(mx + 10, yy, nm, fontsize=6.5, va="center", ha="right",
                color=C_INK, fontweight="bold")
    ax.text(mx + 13, mic_y["L/R"] + 6, "L/R obavezno na GND — inače tišina",
            fontsize=5.5, ha="center", va="center", color=C_WARN, fontweight="bold")

    dcx, dcy = 5, my + 42
    ax.add_patch(FancyBboxPatch((dcx, dcy), 25, 28,
                                boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#fff7ed", ec=C_WARN, lw=0.8, ls="--", zorder=2))
    ax.text(dcx + 12.5, dcy + 5, "dekapling", fontsize=6.5, ha="center",
            color=C_WARN, fontweight="bold")
    ax.text(dcx + 12.5, dcy + 10.5, "470 nF  (474)", fontsize=5.5, ha="center", color=C_INK)
    ax.text(dcx + 12.5, dcy + 15, "10 µF  (+ na VDD)", fontsize=5.5, ha="center", color=C_INK)
    ax.text(dcx + 12.5, dcy + 21, "lemi se NA PADOVE\nMIKROFONA, ne na ploču",
            fontsize=5, ha="center", color=C_WARN, linespacing=1.4)
    ax.plot([dcx + 25, mx + 6], [dcy + 12, mic_y["VDD"]], color=C_WARN, lw=0.6, ls=":")

    # konektor K-MIK na ploči
    kmx = 86
    ax.add_patch(FancyBboxPatch((kmx - 3, mic_y["VDD"] - 4), 6, 5 * 9 + 8,
                                boxstyle="round,pad=0,rounding_size=1",
                                fc="#e5e7eb", ec="#9ca3af", lw=0.7, zorder=2))
    ax.text(kmx, mic_y["VDD"] - 7, "K-MIK", fontsize=5.5, ha="center", color=C_INK,
            fontweight="bold")
    for i, (nm, col) in enumerate(K_MIC):
        yy = mic_y[nm]
        ax.add_patch(Circle((kmx, yy), 1.0, fc=col, ec="#6b7280", lw=0.4, zorder=4))
        ax.plot([mx + 14, kmx - 1.4], [yy, yy], color=col, lw=1.3,
                solid_capstyle="round", zorder=1)

    for a, b in (("VDD", "J1-1"), ("SCK", "GPIO4"), ("WS", "GPIO5"), ("SD", "GPIO6")):
        xb, yb = lp[b]
        col = dict(K_MIC)[a]
        xm = kmx + 6 + list(dict(K_MIC)).index(a) * 3.4
        ax.plot([kmx + 1.4, xm, xm, xb], [mic_y[a], mic_y[a], yb, yb], color=col, lw=1.3,
                solid_capstyle="round", solid_joinstyle="round", zorder=1)
    xb, yb = lp["GND"]
    for a, xm in (("GND", 95), ("L/R", 99)):
        ax.plot([kmx + 1.4, xm, xm, xb], [mic_y[a], mic_y[a], yb, yb], color=C_BLACK,
                lw=1.3, solid_capstyle="round", solid_joinstyle="round", zorder=1)

    # ---- LED
    rx = 212
    for i, (nm, gp, col, note) in enumerate(
            [("zelena LED", "GPIO2", C_GRN, "status — pet obrazaca"),
             ("crvena LED", "GPIO11", C_RED, "alarm")]):
        yy = 44 + i * 28
        ax.text(rx, yy, nm, fontsize=7.5, color=C_INK, fontweight="bold")
        ax.plot([rx, rx + 10], [yy + 8, yy + 8], color=C_INK, lw=1.0)
        ax.add_patch(Rectangle((rx + 10, yy + 5.6), 9, 4.8, fc="#e8dcc0",
                               ec="#8b7355", lw=0.7, zorder=3))
        ax.text(rx + 14.5, yy + 8, "330 Ω", fontsize=5, ha="center", va="center", zorder=4)
        ax.plot([rx + 19, rx + 27], [yy + 8, yy + 8], color=C_INK, lw=1.0)
        ax.add_patch(Circle((rx + 30, yy + 8), 3, fc=col, ec="#3f3f46", lw=0.6, zorder=3))
        ax.text(rx + 30, yy + 13.5, "A", fontsize=5, ha="center", color=C_MUTED)
        ax.plot([rx + 33, rx + 42], [yy + 8, yy + 8], color=C_BLACK, lw=1.0)
        ax.text(rx + 44, yy + 8, "GND", fontsize=6, va="center", color=C_INK)
        ax.text(rx, yy + 16, f"{gp} → otpornik → anoda;  katoda → GND",
                fontsize=5.5, color=C_MUTED)
        ax.text(rx, yy + 20.5, note, fontsize=5.5, color=C_MUTED, style="italic")
        xb, yb = lp[gp]
        ax.plot([xb, rx - 5, rx - 5, rx], [yb, yb, yy + 8, yy + 8], color=col,
                lw=1.3, zorder=1)

    # ---- taster
    yy = 104
    ax.text(rx, yy, "taster (arkadni 30 mm) — VAN PLOČE", fontsize=7.5, color=C_INK,
            fontweight="bold")
    ax.add_patch(Circle((rx + 12, yy + 13), 7, fc="#2f6fd0", ec="#1e40af", lw=0.8, zorder=3))
    ax.plot([rx + 19, rx + 32], [yy + 10, yy + 10], color=C_GRY, lw=1.2)
    ax.plot([rx + 19, rx + 32], [yy + 16, yy + 16], color=C_BLACK, lw=1.2)
    ax.text(rx + 34, yy + 10, "K-TAS 1 → GPIO10", fontsize=6, va="center", color=C_INK)
    ax.text(rx + 34, yy + 16, "K-TAS 2 → GND", fontsize=6, va="center", color=C_INK)
    ax.text(rx, yy + 24, "bez otpornika — interni pull-up je uključen u kodu",
            fontsize=5.5, color=C_MUTED)
    xb, yb = lp["GPIO10"]
    ax.plot([xb, rx - 9, rx - 9, rx + 32], [yb, yb, yy + 10, yy + 10], color=C_GRY,
            lw=1.3, zorder=1)

    # ---- konektor K-M
    kx, ky = 204, 138
    ax.add_patch(FancyBboxPatch((kx, ky), 78, 40,
                                boxstyle="round,pad=0,rounding_size=2",
                                fc="#faf5ff", ec=C_LOAD, lw=1.0, zorder=1))
    ax.text(kx + 4, ky + 7, "K-M  1×4  →  ploča M", fontsize=7.5,
            color=C_LOAD, fontweight="bold")
    for i, (nm, col) in enumerate(K_M):
        yy2 = ky + 14 + i * 6.2
        ax.add_patch(Circle((kx + 6, yy2), 1.1, fc=col, ec="#6b7280", lw=0.4, zorder=3))
        ax.text(kx + 10, yy2, nm, fontsize=5.6, va="center", color=C_INK,
                fontweight="bold")
        tgt = ["→  3V3 šina ploče U", "→  GND šina ploče U",
               "→  GPIO8   (J1-12)", "→  GPIO9   (J1-15)"][i]
        ax.text(kx + 26, yy2, tgt, fontsize=5.3, va="center", color=C_MUTED)
    for gp in ("GPIO8", "GPIO9"):
        xb, yb = lp[gp]
        ax.text(bx + 34, yb, "→ K-M", fontsize=5.5, va="center", color="#9ca3af",
                style="italic")

    panel(ax, 8, 160, 190, 32, "Napajanje ploče U — dva režima, nikad oba",
          ["NORMALAN RAD:  powerbank → USB-C na S3 → onboard LDO → 3,3 V → 3V3 šina.  "
           "K-M ostaje prazan.",
           "E5 MJERENJE:   USB OTKAČEN.  Ploča M → K-M pin 1 → 3V3 šina napaja cijelu ploču U.",
           "Powerbank se za E5 ne koristi — gasi se pri maloj struji. Na ploču M ide "
           "zidni punjač 5 V."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.4, lh=5.6)

    footer(ax, "Strana 2/7 — logička šema ploče U.  Izvor: pins.h + plan-dvije-plocice.md", "")
    save(pdf, fig, 2)


# ================================================= crtač ploče U
def draw_board_u(ax, ox, oy, s, detail):
    """Perfboard 100×50 mm (18×38 rupa) — samo uređaj, bez mjerne grane.

    Ploca stoji uspravno: 50 mm je sirina (18 kolona), 100 mm visina (38 redova).
    Mikro Princ „Test ploca 100x50 tacke", ident 057516.
    """
    NC, NR = 18, 38
    p = PITCH * s
    bw, bh = 50.0 * s, 100.0 * s
    gx = ox + (bw - (NC - 1) * p) / 2
    gy = oy + (bh - (NR - 1) * p) / 2
    f = s

    def hole(c, r):
        return gx + (c - 1) * p, gy + (r - 1) * p

    ax.add_patch(FancyBboxPatch((ox, oy), bw, bh, boxstyle="round,pad=0,rounding_size=1.5",
                                fc=C_PCB, ec="#1b5e37", lw=1.0, zorder=1))
    for cc, rr in ((3.4 * s, 3.4 * s), (bw - 3.4 * s, 3.4 * s),
                   (3.4 * s, bh - 3.4 * s), (bw - 3.4 * s, bh - 3.4 * s)):
        ax.add_patch(Circle((ox + cc, oy + rr), 1.6 * s, fc="#f4f4f5", ec="#9ca3af",
                            lw=0.5, zorder=2))
    for c in range(1, NC + 1):
        for r in range(1, NR + 1):
            x, y = hole(c, r)
            ax.add_patch(Circle((x, y), 0.92 * s, fc=C_PAD, ec="#a8905a",
                                lw=0.25 * s, zorder=2))
            ax.add_patch(Circle((x, y), 0.44 * s, fc="#1f4d33", ec="none", zorder=3))
    step = 1 if detail else 2
    lab_x = ox - 3.0 * s
    num_x = lab_x - (17.0 * s if detail else 0.0)
    for c in range(1, NC + 1, step):
        x, _ = hole(c, 1)
        ax.text(x, oy - 2.6 * s, str(c), fontsize=4.5 * f, ha="center", va="center",
                color=C_MUTED)
    for r in range(1, NR + 1, step):
        _, y = hole(1, r)
        ax.text(num_x, y, str(r), fontsize=4.5 * f, ha="center", va="center",
                color=C_MUTED)

    # --- ESP32-S3: J1 = kol 3, J3 = kol 12, pinovi red 4..25
    j1c, j3c, r0 = 3, 12, 4
    xj1, yj1 = hole(j1c, r0)
    xj3, _ = hole(j3c, r0)
    ax.add_patch(FancyBboxPatch((xj1 - 1.3 * s, yj1 - 4.8 * s),
                                (xj3 - xj1) + 2.6 * s, (53.34 + 9.6) * s,
                                boxstyle="round,pad=0,rounding_size=1.2",
                                fc="#1f2937", ec="#0f172a", lw=0.9, alpha=0.97, zorder=6))
    ax.text((xj1 + xj3) / 2, yj1 + 6 * s, "ESP32-S3", fontsize=6 * f, ha="center",
            color="white", fontweight="bold", zorder=7)
    ax.text((xj1 + xj3) / 2, yj1 + 10 * s, "DevKitC-1", fontsize=5 * f, ha="center",
            color="#9ca3af", zorder=7)
    ax.text((xj1 + xj3) / 2, yj1 + 14.5 * s, "63,0 × 25,5 mm", fontsize=4.2 * f,
            ha="center", color="#9ca3af", zorder=7)
    ax.text((xj1 + xj3) / 2, yj1 + 19 * s, "na ženskim headerima\n1×22, VADIV",
            fontsize=3.9 * f, ha="center", color="#9ca3af", zorder=7, linespacing=1.4)
    ax.text((xj1 + xj3) / 2, yj1 - 7.6 * s, "USB-C  ←  powerbank", fontsize=4.5 * f,
            ha="center", color=C_INK, zorder=9, bbox=BB)

    for i, nm in enumerate(J1):
        x, y = hole(j1c, r0 + i)
        if nm in USED_J1:
            col, tag = USED_J1[nm]
        elif nm == "3V3":
            col, tag = C_RED, "3V3"
        elif nm == "G":
            col, tag = C_BLACK, "GND"
        else:
            col, tag = "#4b5563", None
        ax.add_patch(Circle((x, y), 1.05 * s, fc=col, ec="#0f172a", lw=0.3 * s, zorder=8))
        if tag and detail:
            ax.plot([lab_x + 0.8 * s, x - 1.6 * s], [y, y], color=col, lw=0.5 * s,
                    ls=(0, (2, 1.5)), zorder=5)
            ax.text(lab_x, y, f"{nm} · {tag}" if nm.isdigit() else tag,
                    fontsize=4.2 * f, ha="right", va="center", color=C_INK,
                    fontweight="bold", zorder=9)
    J3_USED = {"2": (C_GRN, "2 · LED zel."), "TX": ("#0ea5e9", "TX · 43"),
               "RX": ("#84cc16", "RX · 44")}
    for i, nm in enumerate(J3):
        x, y = hole(j3c, r0 + i)
        if nm in J3_USED:
            col, lab = J3_USED[nm]
        else:
            col, lab = (C_BLACK if nm == "G" else "#4b5563"), None
        ax.add_patch(Circle((x, y), 1.05 * s, fc=col, ec="#0f172a", lw=0.3 * s, zorder=8))
        if lab and detail:
            ax.text(x + 2.4 * s, y, lab, fontsize=4.2 * f, va="center",
                    color=C_INK, fontweight="bold", zorder=9, bbox=BB)

    # --- konektori na desnoj strani, kolona 20
    def connector(col_i, row0, pins, name):
        x0, y0 = hole(col_i, row0)
        ax.add_patch(FancyBboxPatch((x0 - 1.4 * s, y0 - 1.4 * s), 2.8 * s,
                                    (len(pins) - 1) * p + 2.8 * s,
                                    boxstyle="round,pad=0,rounding_size=0.6",
                                    fc="#e5e7eb", ec="#6b7280", lw=0.6, zorder=6))
        for i, (nm, col) in enumerate(pins):
            x, y = hole(col_i, row0 + i)
            ax.add_patch(Circle((x, y), 1.05 * s, fc=col, ec="#0f172a",
                                lw=0.3 * s, zorder=8))
            if detail:
                ax.text(x + 2.6 * s, y, nm, fontsize=4.0 * f, va="center",
                        color=C_INK, fontweight="bold", zorder=9, bbox=BB)
        if detail:
            ax.text(x0, y0 - 4.4 * s, name, fontsize=4.4 * f, ha="center",
                    color=C_INK, fontweight="bold", zorder=9, bbox=BB)

    connector(16, 3, K_MIC, "K-MIK → INMP441")
    connector(16, 12, K_BTN, "K-TAS → taster")
    connector(16, 17, K_M, "K-M → ploča M")
    connector(16, 24, K_UART, "K-UART → USB-TTL")

    # --- LED + otpornici ispod S3
    for cc, col, tag in ((4, C_GRN, "GPIO2"), (10, C_RED, "GPIO11")):
        r1, r2 = hole(cc, 30), hole(cc + 2, 30)
        ax.add_patch(Rectangle((r1[0], r1[1] - 1.3 * s), r2[0] - r1[0], 2.6 * s,
                               fc="#e8dcc0", ec="#8b7355", lw=0.5, zorder=7))
        lx, ly = hole(cc + 2, 33)
        ax.add_patch(Circle((lx, ly), 2.4 * s, fc=col, ec="#3f3f46", lw=0.5, zorder=7))
        if detail:
            ax.text((r1[0] + r2[0]) / 2, r1[1] - 2.2 * s, "330 Ω", fontsize=3.9 * f,
                    ha="center", va="bottom", color=C_INK, zorder=9, bbox=BB)
            ax.text(lx + 3.4 * s, ly, tag, fontsize=3.9 * f, ha="left", va="center",
                    color=C_INK, zorder=9, bbox=BB)

    # --- šine na dnu
    for rr, col, lab in ((37, C_BLACK, "GND"), (38, C_RED, "3V3")):
        s0, s1 = hole(2, rr), hole(NC - 1, rr)
        ax.plot([s0[0], s1[0]], [s0[1], s1[1]], color=col, lw=2.4 * (1 + (s - 1) * 0.6),
                solid_capstyle="round", zorder=5)
        if detail:
            ax.plot([lab_x + 0.8 * s, s0[0]], [s0[1], s0[1]], color=col, lw=0.5 * s,
                    ls=(0, (2, 1.5)), zorder=5)
            ax.text(lab_x, s0[1], lab + " šina", fontsize=4.2 * f, ha="right",
                    va="center", color=col, fontweight="bold", zorder=9)
    return (ox, oy, bw, bh)


# ============================================================ STRANA 3
def page_board_u(pdf):
    fig, ax = new_page(
        pdf, "PLOČA U (uređaj) — fizički raspored, uvećano",
        "prototipna ploča 100 × 50 mm  ·  18 × 38 rupa  ·  Mikro Princ „Test ploča 100x50 tačke“, ident 057516")

    s = 1.52
    ox, oy, bw, bh = draw_board_u(ax, 62, 34, s, detail=True)

    nx = ox + bw + 14
    panel(ax, nx, 32, 116, 50, "Šta je NA ovoj ploči",
          ["ESP32-S3-DevKitC-1  — ženski headeri 1×22, kolone 3 (J1) i 12 (J3), redovi 4–25",
           "2 × LED 5 mm + 2 × 330 Ω  — otpornici red 30, LED red 33 (GPIO2 lijevo, GPIO11 desno)",
           "K-MIK 1×6 · K-TAS 1×2 · K-M 1×4 · K-UART 1×3  — kolona 16, redovi 3–26",
           "GND šina (red 37) i 3V3 šina (red 38) — gola kalajisana žica",
           "Ništa drugo. Regulator, senzor struje i 470 µF NISU na ovoj ploči.",
           "Kondenzatori mikrofona NISU na ovoj ploči — oni su na samom mikrofonu."],
          fc="#f1f8f3", ec=C_PCB, tc=C_PCB, fs=5.2, lh=5.4)

    panel(ax, nx, 88, 116, 40, "Šta ide na žice sa ove ploče",
          ["K-MIK → INMP441, 6 žica < 10 cm, GND uz signale, L/R na GND",
           "K-TAS → arkadni taster, 2 žice na faston jezičke",
           "K-M   → mjerni sklop, 4 žice ≈ 20 cm, samo tokom E5 mjerenja",
           "K-UART → USB-TTL adapter, samo kad je USB otkačen (E5)",
           "USB-C → powerbank (u normalnom radu)"],
          fs=5.2, lh=5.4)

    panel(ax, nx, 132, 116, 40, "Provjeriti prije lemljenja",
          ["1.  Pin se traži po OZNACI na silkscreenu, ne po broju rupe — J1/J3 je iz",
           "     Espressif DevKitC-1 v1.1; na klonu provjeri multimetrom.",
           "2.  Prebroj rupe: ovdje je uzeto 18 × 38. Ako ih ima 19 × 39, pomjeri",
           "     sve za jednu — milimetri ostaju isti.",
           "3.  3V3 šina dodiruje SAMO pinove 3V3 i K-M pin 1. Nijedan GPIO na šinu."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.2, lh=5.4)

    panel(ax, nx, 176, 116, 20, "Redoslijed lemljenja ploče U",
          ["1. ženski headeri za S3   2. GND i 3V3 šina   3. otpornici + LED  → test lampica",
           "4. konektori K-MIK / K-TAS / K-M / K-UART   5. mikrofon na žice + dekapling  → test 5 s WAV"],
          fs=5.2, lh=5.4)

    footer(ax, "Strana 3/7 — raspored ploče U.  Ploča 100 × 50 mm, mreža 18 × 38 rupa.",
           "uvećano  —  NE mjeriti sa ove strane")
    save(pdf, fig, 3)


# ================================================= crtač ploče M
def draw_board_m(ax, ox, oy, s, detail):
    """Perfboard 40×60 mm (15×23 rupe) — AMS1117 + INA226 + 470 µF."""
    NC, NR = 15, 23
    p = PITCH * s
    bw, bh = 40.0 * s, 60.0 * s
    gx = ox + (bw - (NC - 1) * p) / 2
    gy = oy + (bh - (NR - 1) * p) / 2
    f = s

    def hole(c, r):
        return gx + (c - 1) * p, gy + (r - 1) * p

    ax.add_patch(FancyBboxPatch((ox, oy), bw, bh, boxstyle="round,pad=0,rounding_size=1.2",
                                fc=C_PCB2, ec="#143a5c", lw=1.0, zorder=1))
    for cc, rr in ((3.0 * s, 3.0 * s), (bw - 3.0 * s, 3.0 * s),
                   (3.0 * s, bh - 3.0 * s), (bw - 3.0 * s, bh - 3.0 * s)):
        ax.add_patch(Circle((ox + cc, oy + rr), 1.4 * s, fc="#f4f4f5", ec="#9ca3af",
                            lw=0.5, zorder=2))
    for c in range(1, NC + 1):
        for r in range(1, NR + 1):
            x, y = hole(c, r)
            ax.add_patch(Circle((x, y), 0.92 * s, fc=C_PAD, ec="#a8905a",
                                lw=0.25 * s, zorder=2))
            ax.add_patch(Circle((x, y), 0.44 * s, fc="#12324f", ec="none", zorder=3))
    if detail:
        for c in range(1, NC + 1):
            x, _ = hole(c, 1)
            ax.text(x, oy - 2.6 * s, str(c), fontsize=4.2 * f, ha="center",
                    va="center", color=C_MUTED)
        for r in range(1, NR + 1):
            _, y = hole(1, r)
            ax.text(ox - 2.6 * s, y, str(r), fontsize=4.2 * f, ha="center",
                    va="center", color=C_MUTED)

    def pin(c, r, col):
        x, y = hole(c, r)
        ax.add_patch(Circle((x, y), 1.05 * s, fc=col, ec="#0f172a", lw=0.3 * s, zorder=8))
        return x, y

    def tag(c, r, txt, dr=0.0, dc=0.0, rot=0, ha="center", va="center", fs=3.7):
        if not detail:
            return
        x, y = hole(c + dc, r + dr)
        ax.text(x, y, txt, fontsize=fs * f, ha=ha, va=va, rotation=rot,
                color=C_INK, fontweight="bold", zorder=10, bbox=BB)

    def header(c0, r0, n, vertical=False):
        x0, y0 = hole(c0, r0)
        w = 2.8 * s if vertical else (n - 1) * p + 2.8 * s
        h = (n - 1) * p + 2.8 * s if vertical else 2.8 * s
        ax.add_patch(FancyBboxPatch((x0 - 1.4 * s, y0 - 1.4 * s), w, h,
                                    boxstyle="round,pad=0,rounding_size=0.6",
                                    fc="#e5e7eb", ec="#6b7280", lw=0.6, zorder=6))

    # --- AMS1117: pinovi red 6, tijelo iznad (OUT lijevo, IN desno)
    a0 = hole(4, 6)
    ax.add_patch(FancyBboxPatch((a0[0] - 1.1 * s, a0[1] - 11.5 * s),
                                20.0 * s, 10.0 * s,
                                boxstyle="round,pad=0,rounding_size=0.8",
                                fc="#2f6fd0", ec="#1e40af", lw=0.8, zorder=6))
    ax.text(hole(7.5, 6)[0], a0[1] - 6.5 * s, "AMS1117-3.3", fontsize=4.6 * f,
            ha="center", color="white", fontweight="bold", zorder=7)
    header(4, 6, 2)
    header(10, 6, 2)
    ams_out = pin(4, 6, C_SRC)
    pin(5, 6, C_BLACK)
    ams_in = pin(10, 6, C_RED)
    pin(11, 6, C_BLACK)
    for cc, nm in ((4, "OUT+"), (5, "OUT−"), (10, "IN+"), (11, "IN−")):
        tag(cc, 6, nm, dr=0.75, rot=90, va="top", fs=3.6)

    # --- 5 V ULAZ, kolona 14, redovi 3-4
    header(14, 3, 2, vertical=True)
    p5 = pin(14, 3, C_RED)
    pin(14, 4, C_BLACK)
    tag(14, 2, "5 V ULAZ", dr=-0.5, dc=-0.4, fs=4.2)
    tag(14, 3, "+5 V", dc=-1.0, ha="right")
    tag(14, 4, "GND", dc=-1.0, ha="right")
    y7 = hole(14, 7)[1]
    ax.plot([p5[0], p5[0], ams_in[0], ams_in[0]], [p5[1], y7, y7, ams_in[1]],
            color=C_RED, lw=1.4 * s, solid_capstyle="round",
            solid_joinstyle="round", zorder=9)

    # --- INA226: pinovi red 18, tijelo iznad
    h0 = hole(4, 18)
    ax.add_patch(FancyBboxPatch((h0[0] - 1.8 * s, h0[1] - 21.4 * s), 20.5 * s, 19.4 * s,
                                boxstyle="round,pad=0,rounding_size=1",
                                fc="#1e5aa8", ec="#143f75", lw=0.8, zorder=6))
    ax.text(h0[0] + 8.4 * s, h0[1] - 15.5 * s, "INA226", fontsize=5.0 * f, ha="center",
            color="white", fontweight="bold", zorder=7)
    ax.add_patch(Rectangle((h0[0] + 4.4 * s, h0[1] - 12.0 * s), 8 * s, 3.4 * s,
                           fc="#2b2b2b", ec="none", zorder=7))
    ax.text(h0[0] + 8.4 * s, h0[1] - 10.3 * s, "R100", fontsize=3.4 * f, ha="center",
            va="center", color="white", zorder=8)
    ax.text(h0[0] + 8.4 * s, h0[1] - 19.2 * s, "20,5 × 19,4 mm  ·  0x44",
            fontsize=3.2 * f, ha="center", color="#9ecbff", zorder=7)
    header(4, 18, 8)
    ina = {}
    for i, (nm, col) in enumerate(INA_PINS):
        ina[nm] = pin(4 + i, 18, col)
        tag(4 + i, 18, nm, dr=-0.75, rot=90, va="bottom", fs=3.6)

    # --- K-U izlaz: kolona 2, redovi 17-20
    header(2, 17, 4, vertical=True)
    ku = {}
    for i, (nm, col) in enumerate(K_M):
        ku[nm] = pin(2, 17 + i, col)
        tag(2, 17 + i, nm, dc=1.0, ha="left", fs=3.6)
    tag(2, 16, "K-U → ploča U", dr=-0.9, dc=0.5, ha="left", fs=4.0)

    # --- 470 µF, vadiv, kolone 13-14 red 20
    header(13, 20, 2)
    cp = pin(13, 20, C_LOAD)
    cm = pin(14, 20, C_BLACK)
    ax.add_patch(Circle(((cp[0] + cm[0]) / 2, cp[1] - 6.0 * s), 4.0 * s, fc="#1c1c1c",
                        ec="#3f3f46", lw=0.7, zorder=5))
    ax.text((cp[0] + cm[0]) / 2, cp[1] - 6.0 * s, "470\nµF", fontsize=3.5 * f,
            ha="center", va="center", color="white", zorder=6, linespacing=1.1)
    tag(13, 21, "+", dr=-0.25, fs=4.4)
    tag(14, 21, "−", dr=-0.25, fs=4.4)
    tag(13.5, 20, "470 µF VADIV", dr=-4.4, fs=3.4)

    # --- GND šina, red 22
    g0, g1 = hole(2, 22), hole(14, 22)
    ax.plot([g0[0], g1[0]], [g0[1], g1[1]], color=C_BLACK,
            lw=2.2 * (1 + (s - 1) * 0.6), solid_capstyle="round", zorder=5)
    ax.plot([cm[0], cm[0]], [cm[1], g1[1]], color=C_BLACK, lw=1.3 * s, zorder=5)
    tag(8, 22, "GND šina", dr=0.7, fs=4.0)

    # --- čvor 3V3 IZVOR: AMS OUT+ → INA IN+ i INA VCC   (narandžasto)
    x8 = hole(4, 8)[1]
    ax.plot([ams_out[0], ams_out[0], ina["IN+"][0], ina["IN+"][0]],
            [ams_out[1], x8, x8, ina["IN+"][1]], color=C_SRC, lw=1.5 * s,
            solid_capstyle="round", solid_joinstyle="round", zorder=9, alpha=0.92)
    ax.plot([ina["VCC"][0], ina["VCC"][0]], [x8, ina["VCC"][1]], color=C_SRC,
            lw=1.5 * s, solid_capstyle="round", zorder=9, alpha=0.92)
    tag(7.5, 8, "3V3 IZVOR", dr=-0.7, fs=4.0)

    # --- čvor 3V3 POTROŠAČ: INA IN− → K-U 3V3 i 470 µF +   (ljubičasto)
    y19 = hole(5, 19)[1]
    ax.plot([ina["IN−"][0], ina["IN−"][0], cp[0], cp[0]],
            [ina["IN−"][1], y19, y19, cp[1]], color=C_LOAD, lw=1.5 * s,
            solid_capstyle="round", solid_joinstyle="round", zorder=9, alpha=0.92)
    ax.plot([ina["IN−"][0], hole(3, 19)[0], hole(3, 19)[0], ku["3V3"][0]],
            [y19, y19, ku["3V3"][1], ku["3V3"][1]], color=C_LOAD, lw=1.5 * s,
            solid_capstyle="round", solid_joinstyle="round", zorder=9, alpha=0.92)
    ax.plot([ina["VBS"][0], ina["VBS"][0]], [ina["VBS"][1], y19], color=C_LOAD,
            lw=1.5 * s, solid_capstyle="round", zorder=9, alpha=0.92)
    tag(9, 19, "3V3 POTROŠAČ", dr=0.7, fs=4.0)
    return ox, oy, bw, bh


# ============================================================ STRANA 4
def page_board_m(pdf):
    fig, ax = new_page(
        pdf, "PLOČA M (mjerna) — logička šema i fizički raspored",
        "ploča 4 × 6 cm (A1938) ili MB-102  ·  15 × 23 rupe  ·  kači se na ploču U "
        "samo za E5 mjerenje potrošnje, pa se skida")

    # ---- logička šema, lijevo
    ax.text(16, 36, "Logička šema — struja ide kroz shunt", fontsize=8,
            color=C_INK, fontweight="bold")

    y = 46
    chip(ax, 16, y, 26, 12, "5 V ULAZ", "#7f1d1d", "#5f1414", fs=5.2)
    ax.text(29, y + 17, "zidni punjač", fontsize=5.0, ha="center", color=C_MUTED)
    ax.text(29, y + 22, "NE powerbank", fontsize=5.0, ha="center", color=C_WARN,
            fontweight="bold")

    chip(ax, 54, y, 30, 12, "AMS1117-3.3", "#2f6fd0", "#1e40af", fs=5.0)
    ax.annotate("", xy=(54, y + 6), xytext=(42, y + 6),
                arrowprops=dict(arrowstyle="->", color=C_RED, lw=1.5))
    ax.text(48, y + 3, "5 V", fontsize=4.6, ha="center", color=C_RED)
    ax.text(69, y + 17, "linearni — bez", fontsize=5.0, ha="center", color=C_MUTED)
    ax.text(69, y + 22, "switching ripple-a", fontsize=5.0, ha="center", color=C_MUTED)

    chip(ax, 96, y, 30, 12, "INA226", "#1e5aa8", "#143f75", fs=5.6)
    ax.annotate("", xy=(96, y + 6), xytext=(84, y + 6),
                arrowprops=dict(arrowstyle="->", color=C_SRC, lw=1.8))
    ax.text(90, y + 3, "IN+", fontsize=4.6, ha="center", color=C_SRC)
    ax.text(111, y + 17, "shunt R100 = 0,1 Ω", fontsize=5.0, ha="center", color=C_MUTED)
    ax.text(111, y + 22, "I2C adresa 0x44", fontsize=5.0, ha="center", color=C_MUTED)

    ax.annotate("", xy=(140, y + 6), xytext=(126, y + 6),
                arrowprops=dict(arrowstyle="->", color=C_LOAD, lw=1.8))
    ax.text(133, y + 3, "IN−", fontsize=4.6, ha="center", color=C_LOAD)
    ax.add_patch(FancyBboxPatch((140, y - 2), 26, 16,
                                boxstyle="round,pad=0,rounding_size=1.5",
                                fc="#faf5ff", ec=C_LOAD, lw=1.0))
    ax.text(153, y + 4, "K-U", fontsize=6.5, ha="center", color=C_LOAD,
            fontweight="bold")
    ax.text(153, y + 10, "→ ploča U", fontsize=5, ha="center", color=C_INK)

    # 470 uF grana
    ax.plot([147, 147], [y + 14, y + 26], color=C_LOAD, lw=1.4)
    ax.plot([147, 147], [y + 32, y + 42], color=C_BLACK, lw=1.4)
    ax.add_patch(Circle((147, y + 29), 3.2, fc="#1c1c1c", ec="#3f3f46", lw=0.7))
    ax.text(153, y + 27, "470 µF — vadiv", fontsize=5.2, va="center", color=C_INK)
    ax.text(153, y + 32, "prvo mjeri BEZ njega", fontsize=4.8, va="center", color=C_MUTED)

    # GND
    ax.plot([20, 166], [y + 42, y + 42], color=C_BLACK, lw=2.0, solid_capstyle="round")
    ax.text(16, y + 42, "GND", fontsize=6, va="center", ha="right", color=C_INK,
            fontweight="bold")
    for xx in (29, 69, 111, 153):
        ax.plot([xx, xx], [y + 12, y + 42], color=C_BLACK, lw=0.9, ls=":")

    # I2C
    ax.plot([105, 105, 162, 162], [y + 12, y + 50, y + 50, y + 14],
            color=C_WHT, lw=1.2)
    ax.plot([111, 111, 158, 158], [y + 12, y + 55, y + 55, y + 14],
            color=C_VIO, lw=1.2)
    ax.text(134, y + 48, "SDA", fontsize=4.8, ha="center", color=C_MUTED, bbox=BB)
    ax.text(134, y + 57, "SCL", fontsize=4.8, ha="center", color=C_MUTED, bbox=BB)

    panel(ax, 16, 114, 152, 32, "Dva 3,3 V čvora — najveća zamka na ovoj ploči",
          ["3V3 IZVOR    = AMS1117 OUT+ → INA226 IN+  i  INA226 VCC   (narandžasto)",
           "3V3 POTROŠAČ = INA226 IN− i VBS → 470 µF → K-U pin 1 → ploča U  (ljubičasto)",
           "Između njih je shunt od 0,1 Ω. Ako ih spojiš, struja zaobiđe shunt: INA226",
           "mjeri nulu, a ploča U i dalje radi — greška se NE vidi bez mjerenja."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.2, lh=4.8)

    panel(ax, 16, 148, 152, 48, "Šta je NA ovoj ploči",
          ["AMS1117-3.3 modul  — ženski header 2 × 1×2, red 6 (OUT kol. 4–5, IN kol. 10–11)",
           "INA226 modul       — ženski header 1×8, red 18, kolone 4–11 (ALE ostaje prazan)",
           "470 µF elektrolit  — VADIV, kolone 13/14 red 20, + na ljubičasti čvor",
           "5 V ULAZ 1×2       — kolona 14, redovi 3–4",
           "K-U 1×4            — kolona 2, redovi 17–20: 3V3 · GND · SDA · SCL",
           "GND šina           — red 22, gola kalajisana žica",
           "Ostale veze (SDA, SCL, GND) nisu crtane — u tabeli su na strani 6.",
           "VARIJANTA A: lab. napajanje da 3,3 V pravo na IN+ → AMS1117 i 5 V ULAZ",
           "otpadaju, a ostatak (INA226 + 470 µF) staje i na MB-102, bez lemljenja."],
          fc="#eff6ff", ec=C_PCB2, tc=C_PCB2, fs=5.2, lh=4.8)

    # ---- fizički raspored, desno
    s = 2.4
    draw_board_m(ax, 182, 40, s, detail=True)
    ax.text(182 + 20 * s, 40 + 60 * s + 7, "sve žice idu sa DONJE strane ploče — "
            "ukrštanja su normalna", fontsize=5.2, ha="center", color=C_MUTED,
            style="italic")

    footer(ax, "Strana 4/7 — ploča M.  Redoslijed pinova INA226 provjeri po silkscreenu svog komada.",
           "uvećano  —  NE mjeriti sa ove strane")
    save(pdf, fig, 4)


# ============================================================ STRANA 5
def page_print_1to1(pdf):
    fig, ax = new_page(
        pdf, "Obje ploče u razmjeri 1:1 — za štampu",
        "štampaj na 100 % (bez 'fit to page'); tada je raster tačno 2,54 mm i "
        "komponente se mogu naslagati direktno na papir")

    draw_board_u(ax, 26, 46, 1.0, detail=False)
    ax.text(51, 42, "PLOČA U — 100 × 50 mm", fontsize=7, ha="center", color=C_PCB,
            fontweight="bold")

    draw_board_m(ax, 96, 46, 1.0, detail=False)
    ax.text(116, 42, "PLOČA M — 40 × 60 mm", fontsize=7, ha="center", color=C_PCB2,
            fontweight="bold")

    nx = 150
    ax.text(nx, 44, "Kako se koristi ova strana", fontsize=8, color=C_INK,
            fontweight="bold")
    for i, t in enumerate([
            "1.  Štampaj na 100 %. U dijalogu za štampu isključi 'fit to page' /",
            "     'scale to fit' — inače štampač smanji stranu i raster nije 2,54 mm.",
            "2.  Provjeri mjerilo lenjirom na skali ispod: 10 podioka = 25,4 mm.",
            "3.  Naslaži stvarne komponente na papir i uporedi ih sa obrisima.",
            "     Tu se vidi da li INA226 i AMS1117 stvarno staju kako je nacrtano.",
            "4.  Tek onda buši/lemi. Oznake pinova su na stranama 3 i 4.",
    ]):
        ax.text(nx, 52 + i * 5.6, t, fontsize=5.8, color=C_INK)

    ax.plot([nx, nx + 25.4], [96, 96], color=C_INK, lw=1.2, solid_capstyle="butt")
    for k in range(11):
        ax.plot([nx + k * 2.54, nx + k * 2.54], [93.5, 96], color=C_INK, lw=0.7)
    ax.text(nx, 101, "25,4 mm = 10 rastera — kontrolna skala", fontsize=5.5, color=C_MUTED)

    panel(ax, nx, 110, 130, 40, "Ovo je predloženi raspored, ne izmjereni",
          ["Obrisi S3 ploče (63,0 × 25,5 mm) i razmak headera (22,86 mm) su iz zvanične",
           "Espressif dokumentacije. Obrisi INA226 (20,5 × 19,4 mm) i AMS1117 (≈ 20 × 10 mm)",
           "su iz fotografija modula u img/ — razmak njihovih pinova nije potvrđen",
           "mjerenjem. Izmjeri ih lenjirom na svojim komadima prije nego išta zalemiš."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.3, lh=5.4)

    panel(ax, nx, 156, 130, 40, "Zašto baš ove dvije veličine",
          ["ESP32-S3-DevKitC-1 je 63 mm dugačak, ploča A1938 je 60 mm — ne staje.",
           "Zato ploča U ide na 100 × 50 mm (Mikro Princ, ident 057516, 144 din):",
           "S3 leži uz dužu stranu, a ostaje blok 33 × 50 mm za konektore, LED i šine.",
           "Postojeća A1938 postaje ploča M — na njoj je popunjeno svega 36 % mreže."],
          fc="#f0f7ff", ec="#7ba7d7", tc="#1e5aa8", fs=5.3, lh=5.4)

    footer(ax, "Strana 5/7 — obje ploče 1:1.  Za oznake pinova vidi strane 3 i 4.")
    save(pdf, fig, 5)


# ============================================================ STRANA 6
def _table(ax, x, y, w, title, rows, tc, rh=5.0):
    ax.text(x, y, title, fontsize=7.5, color=tc, fontweight="bold")
    for lab, fr in (("Veza", 0.0), ("Ide na", 0.34), ("Žica", 0.63),
                    ("Napomena", 0.74)):
        ax.text(x + fr * w, y + 7, lab, fontsize=5.0, fontweight="bold", color=C_MUTED)
    ax.plot([x, x + w], [y + 9, y + 9], color="#d4d4d8", lw=0.6)
    for i, (a, b, col, cn, note) in enumerate(rows):
        yy = y + 13.5 + i * rh
        if i % 2 == 0:
            ax.add_patch(Rectangle((x - 1, yy - 2.2), w + 2, rh - 0.5, fc="#f8fafc",
                                   ec="none"))
        ax.text(x, yy, a, fontsize=4.5, va="center", color=C_INK)
        ax.text(x + 0.34 * w, yy, b, fontsize=4.5, va="center", color=C_INK)
        if col:
            ax.add_patch(Circle((x + 0.645 * w, yy), 0.9, fc=col, ec="#9ca3af", lw=0.3))
        ax.text(x + 0.665 * w, yy, cn, fontsize=4.2, va="center", color=C_MUTED)
        crit = any(k in note for k in ("obavezno", "MIKROFONU", "SERIJI", "otkačen",
                                       "ne mjeri"))
        ax.text(x + 0.74 * w, yy, note, fontsize=4.2, va="center",
                color=C_WARN if crit else C_MUTED,
                fontweight="bold" if crit else "normal")
    return y + 13.5 + len(rows) * rh


def page_tables(pdf):
    fig, ax = new_page(pdf, "Tabele veza",
                       "svaka veza koja se lemi, razdvojena po pločama — 41 stavka")

    y = _table(ax, 16, 34, 128, "PLOČA U — uređaj  (21 veza)", NETS_U, C_PCB)
    _table(ax, 16, y + 8, 128, "INTERFEJS  K-M ↔ K-U  (4 žice, ≈ 20 cm)", NETS_IF, C_LOAD)

    y = _table(ax, 152, 34, 128, "PLOČA M — mjerna  (16 veza)", NETS_M, C_PCB2)
    panel(ax, 152, y + 8, 128, 34, "Redoslijed puštanja u rad",
          ["1.  Zalemi ploču U → radi na powerbanku → demo sa ventilatorom je gotov.",
           "2.  Tek onda ploča M. Prije prvog spajanja: izmjeri AMS1117 OUT+ (≈ 3,3 V)",
           "     i provjeri otpornost IZVOR ↔ POTROŠAČ — mora biti ≈ 0,1 Ω, ne 0 Ω.",
           "3.  Otkači USB → ubodi K-M → uključi punjač. Mjeri prvo BEZ 470 µF."],
          fc="#fff7ed", ec=C_WARN, tc=C_WARN, fs=5.0, lh=5.0)

    footer(ax, "Strana 6/7 — tabele veza.  Provjeri svaku stavku multimetrom prije napajanja.", "")
    save(pdf, fig, 6)


# ============================================================ STRANA 7
def page_bom(pdf):
    fig, ax = new_page(pdf, "Spisak komponenti po pločama",
                       "šta se kupuje, šta već imaš, i na koju ploču ide")

    def bom(x, y, w, title, rows, tc, fc, ec):
        h = 11 + len(rows) * 4.6
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2",
                                    fc=fc, ec=ec, lw=0.85))
        ax.text(x + 4, y + 6.5, title, fontsize=6.8, color=tc, fontweight="bold")
        for i, (nm, kom, opis, st) in enumerate(rows):
            yy = y + 12 + i * 4.6
            ax.text(x + 4, yy, nm, fontsize=4.5, va="center", color=C_INK,
                    fontweight="bold")
            ax.text(x + 0.40 * w, yy, kom, fontsize=4.3, va="center", color=C_MUTED)
            ax.text(x + 0.46 * w, yy, opis, fontsize=4.3, va="center", color=C_MUTED)
            ax.text(x + w - 4, yy, st, fontsize=4.3, va="center", ha="right",
                    color=C_WARN if "KUPITI" in st or "donijeti" in st else "#15803d",
                    fontweight="bold")
        return y + h + 5

    def card(x, y, w, name, sub, items):
        h = 12 + len(items) * 4.8
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=2",
                                    fc="#f8fafc", ec="#cbd5e1", lw=0.8))
        ax.text(x + 4, y + 6, name, fontsize=6.8, color=C_INK, fontweight="bold")
        ax.text(x + 0.42 * w, y + 6, sub, fontsize=4.6, color=C_MUTED)
        for i, t in enumerate(items):
            ax.text(x + 5, y + 11.5 + i * 4.8, "·  " + t, fontsize=4.6, color=C_INK)
        return y + h + 5

    lx, rx, w = 16, 152, 131
    y = bom(lx, 32, w, "PLOČA U — na ploču", BOM_U, C_PCB, "#f1f8f3", C_PCB)
    y = bom(lx, y, w, "PLOČA U — van ploče, na žicama", BOM_U_OFF, C_PCB,
            "#f8fafc", "#cbd5e1")
    card(lx, y, w, "INMP441 + pasivne", "šta gledati na komadu",
         ["6 pada u 2 reda po 3 (ne 1×6!) — MEMS u sredini, oznaka 441",
          "L/R → GND = lijevi kanal;  sound port se NE dira",
          "100 nF keramika — nije polarizovan, lemi se na padove mikrofona",
          "10 µF — pruga / kraća nožica = minus → GND mikrofona",
          "LED — duža nožica = anoda;  330 Ω = narandž./narandž./smeđa"])

    y = bom(rx, 32, w, "PLOČA M — na ploču", BOM_M, C_PCB2, "#eff6ff", C_PCB2)
    y = bom(rx, y, w, "PLOČA M — van ploče", BOM_M_OFF, C_PCB2, "#f8fafc", "#cbd5e1")
    y = card(rx, y, w, "INA226", "20,5 × 19,4 mm, plava ploča",
             ["1×8: IN+ IN− VBS ALE SDA SCL GND VCC — provjeri po silkscreenu",
              "JEDAN shunt R100 = 0,1 Ω;  I2C adresa 0x44 (potvrđeno)",
              "VBS → 3V3 POTROŠAČ (firmware čita bus i power);  ALE ostaje prazan",
              "VCC ide na 3V3 IZVOR (prije shunta) — vlastita struja se ne mjeri"])
    card(rx, y, w, "AMS1117-3.3", "≈ 20 × 10 mm, plava ploča",
         ["4 pina: IN+ IN− / OUT+ OUT− — pinovi su već zalemljeni",
          "izmjeri izlaz (≈ 3,3 V) prije nego išta spojiš na njega",
          "nikad USB i eksterno 3V3 istovremeno",
          "ulaz: presječen USB kabl sa zidnog punjača (crvena +5 V, crna GND)"])

    footer(ax, "Strana 7/7 — spisak komponenti.  Cijene: mikroprinc.com i elektromodul.rs, 19.08.2026.", "")
    save(pdf, fig, 7)


def main():
    out = DOCS / "sema-sklopa.pdf"
    with PdfPages(out) as pdf:
        page_overview(pdf)
        page_schema_u(pdf)
        page_board_u(pdf)
        page_board_m(pdf)
        page_print_1to1(pdf)
        page_tables(pdf)
        page_bom(pdf)
        pdf.infodict()["Title"] = ("ASD — sema sklopa, dvije plocice "
                                   "(uredjaj + mjerna)")
    print("OK:", out)


if __name__ == "__main__":
    main()
