# TELFOR 2026 — stanje pred predaju

Revizija: 06.09.2026. Word izvoz: **4 A4 strane, dvije kolone**, dvije slike,
tri tabele. Sadržaj je usklađen sa istim zapisima kao master rad.

**Rok je produžen na 4. oktobar 2026.** To potvrđuju
[početna stranica](https://www.telfor.rs/en/) i
[srpsko uputstvo za autore](https://www.telfor.rs/sr/autori/).
Engleska podstranica je pri provjeri još prikazivala stari 4. septembar.

## Izvori i gradnja

| Fajl | Namjena |
|---|---|
| [build_paper.py](build_paper.py) | tekst i gradnja iz IEEE A4 šablona |
| [../rezultati.py](../rezultati.py) | zajednički izbor prozora i medijane |
| [make_figures.py](make_figures.py) | šema i trase iz mjerenja |
| [../render_word.ps1](../render_word.ps1) | polja, prelom i izvoz PDF-a kroz Word |
| [check_todo.py](check_todo.py) | provjera oznake copyright podnožja |

```powershell
python -m pip install -r radovi/requirements.txt
python radovi/telfor2026/build_paper.py
./radovi/render_word.ps1 -Paths @('radovi/telfor2026/telfor2026_asd_esp32s3.docx')
```

Generator prepisuje DOCX. Izmjene teksta prvo unijeti u izvor.
Tabele više ne miješaju sve označene prozore sa podskupom za metrike.
Apstrakt, rezultati i zaključak navode GUIDED25 FAIL i ograničenja tona.
Vrijeme obrade od 716 ms odvojeno je od akvizicije i ukupne latencije.

## Preostalo

- Mentor i koautor treba da pregledaju i odobre konačni rukopis i autorstvo.
- Copyright oznaku iz registracionog sistema unijeti u podnožje prve strane;
  trenutno je jedna TODO oznaka. Broj se ne pretpostavlja.
- Finalni PDF provjeriti kroz PDF eXpress. Lokalni Word izvoz nije PDF eXpress potvrda.
- Registraciju, uplatu i prezentaciju završiti prema
  [uputstvu organizatora](https://registration.telfor.rs/Info/InstructionsForAuthors).
- Prije javnog objavljivanja rukopisa potvrditi uslove originalnosti i
  odnos preprinta prema prijavi. Repo za sada ostaje privatan.

Autorski blok sa mentorom odgovara redovnoj prijavi. Studentska sekcija
ima posebne uslove autorstva i objavljivanja; raniji poziv iz 2025. više se
ne koristi kao važeći izvor. Prihvaćen i prezentovan redovan rad dostavlja
se radi mogućeg uključivanja u IEEE Xplore; samo pisanje ili prihvatanje
rukopisa to ne garantuje.

Zahvalnica kratko navodi pomoć OpenAI Codex-a u sastavljanju i reviziji
teksta i provjeri tabela, prema [IEEE smjernici](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/).
Brojke dolaze iz zadržanih mjernih artefakata. Zahvalnica ne zamjenjuje
autorsku provjeru rukopisa i izvora.
