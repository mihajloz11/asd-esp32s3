# Master rad — stanje pred predaju

Revizija: 06.09.2026. Tekst je usklađen sa izvornim rezultatima i pregledan
prema sačuvanom uputstvu v8 i FTN šablonima. Završni Word izvoz od 07.09.2026.
daje **42 strane u obje varijante**, 6 slika, 20 numerisanih tabela i 12 referenci.

| Fajl | Namjena |
|---|---|
| [rad_tekst.py](rad_tekst.py) | zajednički izvor teksta, ijekavica |
| [build_rad.py](build_rad.py) | FTN stilovi, preslovljavanje i Word polja |
| [../rezultati.py](../rezultati.py) | tabele završnih fizičkih proba iz CSV-a |
| [make_slike.py](make_slike.py) | šeme i grafikoni |
| [../render_word.ps1](../render_word.ps1) | osvježavanje polja i izvoz kroz instalirani Word |

```powershell
python -m pip install -r radovi/requirements.txt
python radovi/master-rad/build_rad.py
./radovi/render_word.ps1 -Paths @('radovi/master-rad/master_rad_asd_esp32s3_cir.docx','radovi/master-rad/master_rad_asd_esp32s3_lat.docx')
```

Generator prepisuje DOCX; sadržajne izmjene treba unijeti u izvor prije
ponovne gradnje. PDF se regeneriše i lokalno je sačuvan uz DOCX.

## Šta je ispravljeno

- Razdvojeni razvojni AUC za deset prozora i odvojena referenca za dvadeset.
- Objašnjeni razvojni izbor modela i granice normal-only metodologije.
- Potpun postupak kalibracije traje oko 13,57 min u završnim sesijama;
  ranijih 115 s ne opisuje DERIVE i VERIFY.
- Tabele koriste 43/65 i 99/115 DET prozora sa istim filterom; HOLD ostaje uključen.
- GUIDED25 FAIL i neizmjeren oporavak nakon tona navedeni su u izvodu,
  rezultatima i zaključku.
- Ispravljeni logaritamske jedinice, 38 Welch segmenata, histereza i brojač trajnosti.
- Dodato ograničenje osam praznih PSD traka; ništa nije mijenjano u firmware-u.
- Broj strana u obje dokumentacijske informacije sada je Word NUMPAGES polje.

Trase se čitaju iz sačuvanih CSV-a. Šeme su autorski crteži, a grafikon
istorijskog napretka koristi vrijednosti zapisane u razvojnoj dokumentaciji;
te faze nisu kontrolisano poređenje sa potpuno jednakim protokolima.

## Formalno otvoreno

1. Komisija u KDI/KWD: predsjednik i član, četiri TODO pojave.
2. Izjava o akademskoj čestitosti: originalni obrazac iz uputstva v8 sadrži
   izjavu o nekorišćenju generisanja sadržaja. Ona se ne može potpisati kao
   takva nakon pomoći u sastavljanju teksta. U dokumentu je ostavljeno mjesto
   za zvaničnu izjavu usaglašenu sa mentorom; originalno uputstvo nije mijenjano.
3. Način dostavljanja digitalnog priloga: privatni repo ili odobrena javna
   verzija; nije obavezno promijeniti vidljivost repoa radi predaje.
4. Mentorov pregled, pregled druge osobe, komisija i potpisi ostaju ljudske
   i administrativne stavke. Ova revizija ih ne označava kao završene.
5. Uslov publikacije treba potvrditi sa mentorom i službom. Napisani TELFOR
   rukopis sam po sebi nije prihvaćen niti objavljen rad i nije automatski
   zamjena za rad u Zborniku FTN. [FTN postupak](https://deet.ftn.uns.ac.rs/pravilnici/postupak-zavrsetka-master-akademskih-studija-i-postupak-izrade-i-odbrane-master-rada/)
   i [elektronska obrada](https://deet.ftn.uns.ac.rs/wp-content/uploads/2021/03/Elektronska-obrada-zahteva-za-zavrsni-rad.pdf)
   traže evidentiranje publikacije; lokalno uputstvo dodatno opisuje prihvatljive puteve.

Ćirilica prati izričito uputstvo v8; latinica ostaje radna alternativa.
Neplanirana fizička mjerenja ostaju ograničenja, a ne prazna poglavlja ili obećani rezultati.
