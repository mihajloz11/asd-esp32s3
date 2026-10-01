# TELFOR 2026 — stanje pred predaju

Revizija: 01.10.2026. Word i PDF su usaglašeni: tri slike iz mjerenja,
dvije tabele, devet referenci i **4 A4 strane**. PDF je izvezen iz
LibreOffice-a; za predaju ga je bolje izvesti iz Worda (`render_check.py` na Windowsu).
Opis alarma, histereze i promjenljive pobude usklađen je sa završnim
probama i ponavljanjem svih 180 odluka, bez neslaganja.
Provjera tehničkih tvrdnji i ciljane jezičke izmjene opisane su u
[bilješci o reviziji](PROVJERA-2026-10-01.md).

**Rok je 4. oktobar 2026.** ([telfor.rs](https://www.telfor.rs/en/),
[uputstvo za autore](https://www.telfor.rs/sr/autori/))

## Šta je novo u odnosu na verziju od 06.09.

- Naslov: *Anomalous Sound Detection on an ESP32-S3 with On-Device
  Commissioning from Normal Sound*.
- Tabela I poredi autoenkoder (DCASE), log-mel statistiku i PSD, sa
  vremenom računanja na uređaju. Stara tabela osam kandidata i tabela
  vremenskih pravila svedene su na po jednu rečenicu.
- Sl. 2: cijele sesije obje probe, od CAL preko DERIVE/VERIFY do nadzora.
- Sl. 3 i odjeljak V.C–D: naknadna analiza snimljenih obilježja
  ([trial_features](../../results/trial_features/2026-09-25/README.md)).
  Papirić i ton su detektovani po obliku spektra; ton je svirao šest minuta
  poslije oznake kraja; prazne trake nose nivo.
- Epizode se broje iz događaja uređaja: po **jedna** u obje probe
  (host je brojao dvije zbog izbačenog prelaznog prozora).
- Diskusija: HOLD je isti mehanizam koji je propustio papirić i zadržao
  razgovor; p99 od 44 prozora je maksimum, pa jedan prozor postavlja prag.

## Gradnja

```powershell
python -m pip install -r radovi/requirements.txt matplotlib pymupdf
python radovi/telfor2026/make_figures.py
python radovi/telfor2026/build_paper.py
python radovi/telfor2026/render_check.py      # Word na Windowsu, inače LibreOffice
python radovi/check_documents.py --output radovi/telfor2026/preview/checks.json telfor2026
```

Generator prepisuje DOCX. Tekst se mijenja samo u `build_paper.py`.
Izvori brojki: [HANDOFF.md](HANDOFF.md).

## Preostalo prije predaje

- Mentor i koautor pregledaju i odobre rukopis i autorstvo.
- Copyright oznaku iz registracionog sistema unijeti u podnožje prve strane
  kada bude dostupna. Privremena oznaka je uklonjena; broj se ne pretpostavlja.
- PDF provjeriti kroz IEEE PDF eXpress.
- Registracija, uplata i prezentacija prema
  [uputstvu organizatora](https://registration.telfor.rs/Info/InstructionsForAuthors).

Zahvalnica o AI alatima je izbačena 01.10. TELFOR uputstvo ne traži takvu
izjavu, a [IEEE smjernica](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/)
je za jezičku redakciju samo preporučuje. Obavezna je ako je AI generisao
sadržaj rada (tekst, slike, kod); tada se zahvalnica vraća sa tačnim opisom.

Zaključak od 01.10. navodi da su samostalne probe sa dugmetom i LED-ovima,
uključujući gašenje alarma poslije tona, prošle kako je predviđeno. Ostaje
samo mjerenje potrošnje na mjernoj ploči (INA226).
