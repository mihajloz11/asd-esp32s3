# Revizija projekta, 06.09.2026.

Završni pregled dokumenata i sačuvanih fajlova: 07.09.2026.

Pregled obuhvata inventar svih 842 tada praćena fajla, glavni firmware tok,
host protokol, kalibraciju, evaluacione alate, testove, mjerne artefakte,
dokumentaciju i izvore oba rada. Inventar nije tvrdnja da je svaka linija
svih istorijskih režima pojedinačno dokazana ispravnom. Zavisnosti,
raspakovani podaci i generisani build nisu dio ručnog pregleda izvora.

## Sačuvana radna verzija

- Polazni Git HEAD: `34f4fc2`; prethodne lokalne izmjene radova sačuvane su
  prije dorade, pa uključene u završne izvore.
- Firmware, ugrađeni modeli, konfiguracije detektora i sirovi mjerni zapisi
  nisu izmijenjeni. Nije izveden novi build radnog firmware-a, flash ili fizička proba.
- Radni binarni fajl: 354 784 B,
  SHA-256 `9ac2caca2c5010747547d4bb942aae96f700221588a4a6863b5c01948d967813`.
- [baseline.json](baseline.json) sadrži polazni inventar i ponovljene statistike.

## Najvažniji nalazi

| Prioritet | Nalaz | Ishod revizije |
|---|---|---|
| Visok, izvještavanje | `valid_physical_result` tumačen kao uspjeh cijele probe | Ispravljeno u README-u, pregledu proba i oba rada; papirić ima GUIDED25 FAIL |
| Visok, izvještavanje | Tabele koriste sve oznake, a zbirne metrike drugi podskup | Zajednički čitač `radovi/rezultati.py`, 43/65 i 99/115 prozora; HOLD uključen |
| Visok, metodologija | Normal-only fit predstavljen kao potpuna nezavisnost razvojnog izbora od anomalija | Razdvojeni fit i raniji uvid u razvojne rezultate; bez tvrdnje o nezavisnom finalnom testu |
| Srednji, algoritam | Osam praznih PSD traka uvodi osjetljivost na pojačanje | Potvrđeno na neizmijenjenom C kodu, sintetičkim širokopojasnim signalom; model ostaje isti |
| Srednji, audio | `-raw[i]` može preteći za INT32_MIN; konverzija u int16 nema zasićenje | Nalaz statičkog pregleda, ne potvrđen uzrok dosadašnjih problema; buduća izolovana izmjena |
| Srednji, konkurentnost | `dropped` se mijenja u proizvođaču i nulira u drugom toku bez sinhronizacije | Evidentiran rizik izgubljenog inkrementa/snimka stanja; `volatile` ne rješava međuzavisne operacije |
| Srednji, reprodukcija | Stari PSD izvoznik ne potvrđuje identitet trening skupa samo brojem 990 | Sačuvana postojeća zaglavlja; preporučen manifest trening ulaza i hash izvoza |
| Nizak, CI | GITHUB_PATH važi za naredne korake, a isti korak odmah zove GCC | Dopunjena trenutna PATH varijabla; izvršenje udaljenog CI-ja nije pokrenuto |
| Visok, formalno | Stari rok TELFOR-a, nepotpuni preduslovi predaje i netačna spremnost izjave | Ažurirane zasebne liste formalnih stavki uz izvore |

## Brojke koje radovi sada koriste

| Metrika | Papirić | Ton |
|---|---:|---:|
| DET ukupno / za metrike | 65 / 43 | 115 / 99 |
| Alarmni prozori u metrici | 3 | 64 |
| Alarmne epizode prema sačuvanom izvještaju | 2 | 2 |
| Medijana normalne osnove | 1146 | 7085 |
| Medijane izazvane promjene | 30 255; 62 344; 19 844 | 23 574 |
| Ishod | 1/3 blokova, GUIDED25 FAIL | alarm i trajno odstupanje |

Izbor prozora: `protocol_valid=1`, `condition_confirmed=1`,
`transition_window=0`. Grafici zadržavaju sve DET zapise radi kontinuiteta.
Ni oznaka uslova ni pad ocjene ne utvrđuju tačan trenutak promjene jačine
ili gašenja tona. Medijana oporavka 10,08 s za run A ne znači da su svi
oporavci prošli kriterij. Run B nema izmjeren završni oporavak.

Potpun kalibracioni postupak traje oko 13,57 min od komande do nadzora u obje sesije,
a ne 115 s. Alarm ulazi poslije tri pouzdana prekoračenja. Sustained događaj
nastaje na dvanaestom mjerenom alarmnom prozoru, uključujući ulaz; HOLD pauzira
brojanje. To nisu izmjerene latencije od fizičkog početka pobude.

## Provjere

```powershell
.\.venv\Scripts\python.exe -m pytest pc/tests -q
.\.venv\Scripts\python.exe pc/tools/check_schema_consistency.py
.\.venv\Scripts\python.exe pc/tools/probe_psd_gain.py --output results/repository_audit/2026-09-06/gain_probe.json
.\.venv\Scripts\python.exe pc/tools/audit_repository.py --output results/repository_audit/2026-09-06/final.json
```

Osnovna regresija: **478 passed**, provjera šeme PASS. Ovi testovi ne
zamjenjuju hardversko ispitivanje. [gain_probe.json](gain_probe.json) daje
osam praznih traka i maksimalno odstupanje od analitičkog pomjeraja
`2,72e-6`. Promjena amplitude ×2 pomjera popunjene trake za oko `0,05017`,
a prazne za `−0,55189` jedinica logaritamskog obilježja. Uticaj na tačnost
detekcije nije izmjeren. Welch obrađuje 38 kompletnih segmenata.

Word izvoz i broj strana: [document_render.json](document_render.json).
Polja sadržaja, spiskova i NUMPAGES osvježavaju se kroz instalirani Word.
Stranice su izvezene u PDF i vizuelno pregledane, uključujući prelom tabela,
slike, podnožja i priloge. [Provjera dokumenata](document_checks.json) prati
A4 format, broj strana, citate i greške Word polja. Master ima 20 numerisanih
tabela i tri nenumerisane tabele uvodnog dijela; zato Word broji 23 tabele.
Preostale TODO oznake odnose se na formalne stavke, a ne na nedostajuće rezultate.
Formalni preduslovi ostaju u [master listi](../../../radovi/master-rad/PREOSTALO-RAD.md)
i [TELFOR listi](../../../radovi/telfor2026/PREOSTALO-RAD.md).

[Provjera sačuvane verzije](frozen_verification.json) poredi SHA-256 svih
610 postojećih fajlova firmware-a, modela i rezultata sa polaznim inventarom.
Nijedan nije izmijenjen. Poređenje sintaksnog stabla potvrđuje da kraći komentari
u dva host alata nisu promijenili izvršnu logiku.

## Prijedlozi za narednu verziju

1. **Prazne trake.** Napraviti alternativnu mapu sa najmanje jednom FFT
   tačkom po traci, pa ponovo izvesti standardizaciju i kovarijansu samo iz
   normalnog treninga. Prvo provjeriti gain sweep i PC–C slaganje. Ne brisati
   osam dimenzija postojećeg modela bez ponovnog učenja.
2. **Uticaj kovarijanse.** Na normalnim snimcima porediti ograničavanje malih
   varijansi i dijagonalno skupljanje; zasebno pratiti K1 prihvatanje i kasniji
   VERIFY. Ne podešavati granice da papirić iz završne probe naknadno prođe.
3. **Audio rubni slučajevi.** Izdvojiti čistu funkciju konverzije, koristiti
   širi tip za apsolutnu vrijednost i eksplicitno zasićenje. Dodati testove
   INT32_MIN/MAX i granica int16 prije bilo kakvog eksperimentalnog flasha.
4. **Brojači.** Uvesti konzistentan snimak/reset statistike uz odgovarajuću
   sinhronizaciju i test proizvođača/potrošača. Promjena ne smije prikriti
   stvarne gubitke na granici prozora.
5. **Reprodukcija modela.** Izvoznik treba da provjeri imena nizova, oblik,
   konačnost, spisak normalnih trening fajlova i fingerprint svih ulaza.

Prva tačka je novi, numerički potvrđen motiv za eksperiment. Nijedna od ovih
ideja još ne daje dokaz boljeg firmware-a, pa u ovoj reviziji nije napravljena
neispitana zamjena radne verzije. Rizična promjena pripada zasebnoj grani
`codex/...` tek uz novi model i odgovarajuću provjeru.

## Javna objava

Repo ostaje privatan; nije slat drugima niti mu je mijenjana vidljivost.
Polazni pregled tekstualnih fajlova nije našao prepoznatljive privatne ključeve,
GitHub tokene, AWS access key ili obrasce API ključeva. To je ograničena provjera
obrazaca, ne potvrda odsustva svih tajni. [Inventar](baseline.json) navodi
36 fajlova sa lokalnim korisničkim putanjama i/ili identifikatorima uređaja.
Sirovi artefakti nisu prepravljani radi uljepšavanja istorije.

[Pregled Git istorije](history_scan.json) obuhvatio je 1858 objekata svih
lokalno dostupnih referenci: 1039 tekstualnih blobova, približno 37,9 MB.
Nema pogodaka navedenih obrazaca. Binarni kontejneri (196 blobova) i reflog
nisu pregledani ovom provjerom; kontakti i biografija u radovima pregledani
su kroz same dokumente.

Prije objave cijelog postojećeg repoa treba odlučiti:

- da li ostaju lična biografija, kontakti, fotografije i lokalne putanje;
- koji rukopis smije biti javan nakon mentorovog/koautorskog pregleda i
  provjere pravila konferencije;
- da li originalni FTN/IEEE šabloni i materijali drugih autora smiju biti
  dalje distribuirani ili treba ostaviti samo linkove;
- pod kojom licencom se objavljuje sopstveni kod. Nije proizvoljno dodata
  licenca koja bi obuhvatila i tuđe materijale ili DCASE podatke.

`.gitignore` isključuje lokalne kredencijale i pomoćne buildove. To ne uklanja
već praćene fajlove niti mijenja istoriju. Nepredate radove nije opravdano
proglasiti spremnim za javnu objavu samo zato što imaju uredan prelom.

## Izvori pravila, provjereni 06.09.2026.

- FTN: sačuvano uputstvo v8 i MSc šabloni u `radovi/master-rad/sablon/`,
  uz [proceduru DEET-a](https://deet.ftn.uns.ac.rs/pravilnici/postupak-zavrsetka-master-akademskih-studija-i-postupak-izrade-i-odbrane-master-rada/).
- TELFOR: [aktuelni rok i autori](https://www.telfor.rs/sr/autori/),
  [prijava i PDF eXpress](https://registration.telfor.rs/Info/InstructionsForAuthors).
- IEEE: [pomoć alata u generisanju sadržaja](https://open.ieee.org/author-guidelines-for-artificial-intelligence-ai-generated-text/).
