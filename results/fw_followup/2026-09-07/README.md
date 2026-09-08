# Redoslijed proba firmware-a — 07.09.2026.

Sve četiri predložene tačke obrađene su redom. Izmjene su lokalne, bez
push-a ili flešovanja. Originalni `master new` zadržava radni FW; izvori
novih varijanti nalaze se u zasebnom radnom folderu `master-psd-nonempty`.
Taj folder trenutno prikazuje završnu granu `codex/psd-covariance-study`.

| Tačka | Grana i commit | Ishod |
|---|---|---|
| 1. Neprazne PSD trake | `codex/psd-nonempty-bands`, `ee88fc4` | bolji razvojni AUC; naknadno je svih pet preskočenih testova prošlo sa podacima iz glavnog foldera |
| 2. Audio konverzija | `codex/audio-sample-saturation`, `7412e4e` | zasićenje bez promjene u normalnom opsegu; tačan unsigned peak i za INT32_MIN; 22 ciljana testa i build prolaze |
| 3. Statistika | `codex/audio-statistics-sync`, `624e6d3` | sinhronizovani upis/reset i snimak statusa; 26 ciljanih testova, puna regresija 490/490 i build prolaze |
| 4. Kovarijansa | `codex/psd-covariance-study`, `e6dbfc7` | tri dodatne regularizacije daju slabije rangiranje; model nije promijenjen; dvije nove numeričke provjere prolaze |

Grane su uzastopne: tačka 2 sadrži tačku 1, a tačka 3 sadrži tačke 1 i 2.
Tačka 4 dodaje samo računarsku studiju i njene testove/rezultate. Poslije
pune regresije od 490 testova dodate su dvije provjere studije; one su
posebno izvršene, pa nije tvrđen jedan puni poziv sa 492 testa.

## Paketi za buduću fizičku probu

Svaki direktorijum u lokalnom `dist/` sadrži `candidate`, `rollback` i
manifest sa adresama i hash-evima. Kopije su u oba radna foldera.

| Paket | Sadržaj | Aplikacija |
|---|---|---:|
| `psd-nonempty-2026-09-07` | samo tačka 1 | 355104 B |
| `audio-saturation-2026-09-07` | tačke 1 i 2 | 355184 B |
| `audio-stats-sync-2026-09-07` | tačke 1, 2 i 3 | 355328 B |
| `rollback` u svakom paketu | kopija ranije fizički testiranog FW-a | 354784 B |

Prva fizička proba treba da koristi paket sa samo tačkom 1, kako bi se
izolovao uticaj PSD mape. Paketi se zatim mogu porediti redom. Nijedan nije
potvrđen na uređaju. Nova mapa zahtijeva novu normal-only kalibraciju.

Host u ovom projektu uzima hash iz lokalnog firmware build direktorijuma.
Prije snimanja treba uskladiti izabranu granu, build i stvarno flešovan bin;
trenutni build u eksperimentalnom folderu pripada paketu sa tačkama 1–3.
Sa njim se ne smije pripisati porijeklo snimku napravljenom paketom samo
za tačku 1. U ovoj sesiji nije pokretan host za fizičko mjerenje.

## Izvještaji

- [Tačka 1: mapa i dopuna preskočenih provjera](../../psd_nonempty/2026-09-07/README.md)
- [Tačke 2 i 3: konverzija, statistika i buildovi](../../audio_hardening/2026-09-07/README.md)
- [Tačka 4: sve varijante kovarijanse](../../psd_covariance/2026-09-07/README.md)
- [Završna provjera originala i kopiranih paketa](verification.json)

Originalni C izvori i praćeni modeli glavnog foldera odgovaraju njegovom
početnom commitu. Provjeren je i identičan hash originalnog radnog bina.
Ranija revizija dokumenata i necommitovane izmjene glavnog foldera ostaju
sačuvane. Novi razvojni rezultati nisu uneseni kao fizički dokazi u radove.
