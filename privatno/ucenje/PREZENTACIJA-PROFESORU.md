# Akustička detekcija anomalija na ESP32-S3

## 1. Cilj i realizovani sistem

- Jedan INMP441 mikrofon i ESP32-S3.
- Lokalno učenje normalnog zvuka konkretne postavke.
- Autonomno računanje ocjene odstupanja i prijava održane promjene.

![Od učenja na računaru do odluke uređaja](../../photos/sl_sistem.png)

## 2. Podaci i model

- **DCASE 2026, ventilator:** globalni model iz 990 normalnih source snimaka.
- **Finalni opis:** 96 PSD-shape vrijednosti po klipu od približno 10 s.
- **Model:** standardizacija + Ledoit–Wolf kovarijansa + Mahalanobis ocjena.
- Naučene tabele ugrađene u firmware; centar i pragovi prilagođeni lokalno.

## 3. Kako uređaj donosi odluku

**Zvuk → spektar → 96 vrijednosti → score → provjera pouzdanosti → alarm**

| Priprema | Uloga |
|---|---|
| CAL — 10 prozora | lokalni centar i provjera stabilnosti |
| DERIVE — 44 prozora | pragovi iz normalnog rada |
| VERIFY — 22 prozora | odvojena provjera normale |

- Alarm: **3 uzastopna pouzdana prozora** iznad ulaznog praga.
- HOLD: zadržavanje odluke kod nepouzdanog prozora.
- Niži izlazni prag za stabilniji povratak iz alarma.

## 4. Razvojni rezultati na računaru

| Pristup | Fan AUC | Kontekst |
|---|---:|---|
| Raniji autoenkoder, fp32 | 0,4682 | istorijski baseline |
| PSD-shape | 0,8556 ± 0,0240 | 20 razvojnih podjela |
| PSD-shape, k=20 | 0,8666 ± 0,0270 | odvojena PC referenca, 100 podjela |

**AUC mjeri rangiranje, ne procenat tačnosti.** Protokoli se razlikuju; rezultati su razvojni.

- Poređenje Python i C računanja istih obilježja.
- Oko **716 ms računanja** po desetosekundnom prozoru na uređaju.

## 5. Fizičke probe

### Promjena zvuka papirićem

![Score i alarm tokom probe papirićem](../../photos/sl_run_papiric.png)

- Promjena vidljiva u score-u; brojni prozori zadržani kroz HOLD.
- Alarm u **1 od 3 bloka**, uz prenošenje u oporavak.
- **GUIDED25: FAIL.**

### Stabilan ton od 1 kHz

![Score i alarm tokom tonske probe](../../photos/sl_run_ton.png)

- Dva ulaska u alarm i prijava održane promjene.
- Ton je trajao oko šest minuta poslije oznake oporavka.
- Završni povratak u normalu nije potvrđen.

*X: vrijeme; Y: score. Crvena linija: ulazni prag; zelena: izlazni. Plavo: pouzdani prozori; narandžasto: HOLD; crveni trouglovi: alarm.*

## 6. Zaključak i naredni korak

- Realizovan kompletan tok od mikrofona do lokalne odluke.
- Potvrđena detekcija određenih promjena zvuka na jednoj postavci.
- Otvoreno: nestabilne promjene, oporavak i provjera na novim ventilatorima.
- Mehanički uzrok kvara i dugoročna pouzdanost još nijesu potvrđeni.

**Šta prvo: nezavisna proba na drugom ventilatoru ili dorada kalibracije i oporavka?**
