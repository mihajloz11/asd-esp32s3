# INA226 — šta provjeriti (lista za multimetar)

> **Riješeno 10.08.2026:** GND je bio pogrešno spojen na strani ESP32-S3, zbog
> čega su SDA i SCL ostajali na 3,3 V. Modul nije bio pokvaren.
>
> Poslije ispravke GND veze potvrđeno je: SDA/SCL se normalno obaraju, INA226
> odgovara na **0x44**, ID registri su `0x5449`/`0x2260`, a konfiguracija
> `0x4527` i kalibracija `1024` ostaju upisane. Sa nepovezanim IN+/IN− izmjeren
> je očekivani šum šanta od −10 do −7 µV.
>
> Postupak ispod ostaje kao dijagnostička procedura za buduće probleme.

---

## Prije mjerenja

1. **Iskopčaj USB** sa S3. Mjerenje otpora na napojenom kolu ne vrijedi ništa.
2. **Skini sve četiri žice sa modula** (VCC, GND, SDA, SCL). Modul mora biti sam.
3. Multimetar na **otpor (Ω)**, opseg 20 kΩ ako je ručni.

> ⚠️ **Ne koristi zvučnu provjeru (continuity).** Većina multimetara pišti i na
> nekoliko kΩ, pa bi ti ispravan pull-up od 10 kΩ zvučao isto kao kratak spoj.
> To je razlog što je tvoja jučerašnja provjera rekla da je sve čisto.

> ℹ️ **Vrijednost će puzati naviše** — to je kondenzator na modulu koji se puni
> kroz mjernu struju, potpuno normalno. Sačekaj da se umiri ili samo gledaj red
> veličine. Prije mjerenja možeš kratko spojiti sonde obrnuto da ga isprazniš.

---

## 1. Mjerenja — dvije brojke koje sve rješavaju

Pinovi modula, silk redoslijed **s lijeva na desno**:

```
VCC · GND · SDA · SCL · ALE · UBS · IN− · IN+
```

| # | Između | Ispravno | KVAR ako je |
|---|---|---|---|
| 1 | **VCC ↔ SDA** | ~10 kΩ | blizu 0 Ω |
| 2 | **VCC ↔ SCL** | ~10 kΩ | blizu 0 Ω |

To su jedine dvije brojke koje trebam. Zapiši ih.

### Dopunska mjerenja (ako gornja ispadnu 0 Ω)

| # | Između | Ispravno | Znači |
|---|---|---|---|
| 3 | VCC ↔ GND | veliko / raste | ako je 0 Ω → most i na napajanju, opasnije |
| 4 | SDA ↔ SCL | ~20 kΩ (dva pull-upa u nizu) | ako je 0 Ω → most direktno između njih |
| 5 | GND pin modula ↔ GND na S3 | ~0 Ω | provjera da GND uopšte prolazi |

---

## 2. Vizuelna provjera — gdje kalaj najčešće iscuri

Uzmi lupu ili zumiraj telefonom. Gledaj **stranu sa čipom**, ne stranu sa lemovima.

**Glavni osumnjičeni: dva bijela otpornika sa oznakom `103`**, odmah ispod
letvice, uz VCC i GND pin. To su pull-upovi od 10 kΩ. Ako je kalaj procurio
preko jednog od njih, taj otpornik je premošten i njegova linija je direktno
na napajanju — tačno ono što mjerenja pokazuju.

Redom šta gledati:

- [ ] **Preko tijela `103` otpornika** — sitna kuglica kalaja koja spaja obje
      strane otpornika. Ovo je najvjerovatniji uzrok.
- [ ] **Između pada letvice i susjednog otpornika** — kalaj se razlio sa pina
      naniže, do prvog SMD elementa.
- [ ] **Ispod letvice, sa strane čipa** — pogledaj pod uglom, prema svjetlu.
- [ ] **Sitne perlice kalaja** koje su odletjele i zalijepile se drugdje na
      pločicu (dešava se kad kalaj "pukne" pri lemljenju).
- [ ] **Nožice samog čipa** (mali crni SOIC sa oznakom `TI 226`) — most između
      njegovih nožica, naročito prema strani gdje idu SDA/SCL.
- [ ] **Ostaci fluksa** — smeđa ljepljiva prevlaka. Sama po sebi obično ne
      provodi, ali skriva mostove ispod sebe. Očisti izopropanolom pa gledaj ponovo.

---

## 3. Šta uraditi zavisno od nalaza

### Ako je 0 Ω i nađeš most

1. Očisti pletenicom za odlemljivanje ili vrhom lemilice sa malo fluksa.
2. Isperi izopropanolom, sačekaj da se osuši.
3. Izmjeri ponovo — mora pokazati ~10 kΩ.
4. Vrati žice (VCC→3V3, GND→GND, SDA→GPIO 8, SCL→GPIO 9) i javi mi.
   Test na ploči traje deset sekundi — ja flešujem `ASD_INA_TEST` build.

### Ako je 0 Ω a nema vidljivog mosta

Čip je vjerovatno oštećen (pregrijavanje pri lemljenju ili statički
elektricitet). Naruči nov INA226 — 300–500 din na elektromodul.rs.
Sklop ostaje isti, drajver je već napisan.

### Ako je ~10 kΩ (dakle modul je ispravan)

Onda greška nije gdje mislimo i vraćamo se na ožičenje — javi mi brojke,
imam još par testova koje mogu pustiti sa ploče.

---

## 4. Čega se ne treba plašiti

- **Nisi ništa pokvario na S3.** Pinovi GPIO 8 i 9 su izmjereni kao potpuno
  ispravni — obaraju se i puštaju kako treba čim se žice skinu.
- **Mikrofon i cijeli audio lanac rade** i nisu ni na koji način ugroženi.
- **Ovo ne blokira rad na tezi.** Jedino E5 (mjerenje energije) zavisi od
  INA226. Sve ostalo — E1 do E4, živi zvuk, model na čipu — je gotovo ili radi.

---

## Podsjetnik: šta je već isključeno

Da se ne troši vrijeme na ponovnu provjeru:

| Provjereno | Rezultat |
|---|---|
| Pinovi GPIO 8/9 na ploči | ispravni |
| Zamijenjene SDA/SCL | nije to (probano i obrnuto, softverski) |
| Kratak spoj između SDA i SCL linija | nema ga |
| Žice u pogrešnim pinovima ploče | nisu — mapa svih GPIO-a to potvrđuje |
| Pull-up otpornici na modulu | 10 kΩ, ispravna vrijednost (oznaka `103`) |
| Vrijednost otpora koja "raste" pri mjerenju | normalno, kondenzator se puni |
