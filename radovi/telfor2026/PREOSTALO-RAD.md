# TELFOR 2026 — stanje pred predaju

Revizija: 25.09.2026. Rad je prepisan: novi naslov, nova struktura, tri
slike iz mjerenja, dvije tabele, devet referenci. LibreOffice izvoz daje
**4 A4 strane** sa oko pola kolone rezerve; Word prelom treba potvrditi.

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
- Otvoriti DOCX u Wordu, provjeriti prelom (4 strane) i izvesti PDF.
- Copyright oznaku iz registracionog sistema unijeti u podnožje prve strane
  (jedina `[TODO]` oznaka). Broj se ne pretpostavlja.
- PDF provjeriti kroz IEEE PDF eXpress.
- Registracija, uplata i prezentacija prema
  [uputstvu organizatora](https://registration.telfor.rs/Info/InstructionsForAuthors).

Zahvalnica navodi korišćenje alata OpenAI Codex i Anthropic Claude za
jezičku redakciju i provjeru tabela, prema
[IEEE smjernici](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/).
Ako se izmijeni, izjava mora ostati tačna.
