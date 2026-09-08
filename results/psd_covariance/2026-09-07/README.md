# Tačka 4 — kovarijansa i stabilnost normalnih ocjena

Nijedna od tri dodatne varijante nije poboljšala AUC i pAUC prema modelu
sa nepraznim trakama. Zadržan je model iz tačke 1; novi model nije izvezen
u firmware i pragovi nisu podešavani poslije gledanja rezultata.

## Postupak

Četiri varijante i njihove vrijednosti određene su u [planu](plan.json)
prije ove evaluacije. Sve koriste istu nepraznu mapu od 96 PSD traka.
Učenje koristi 990 source-normal snimaka; lokalni centar koristi 10 ili 20
normalnih snimaka iz target skupa. Isti target pool ima 60 normalnih i
50 anomalnih snimaka. Ponovljeno je istih 100 podjela po k iz tačke 1,
sa istim hash-evima ulaznih WAV fajlova i bez preklapanja cal/held podskupova.

Sva četiri modela i normalne dijagnostičke ocjene zamrznuti su prije čitanja
obilježja anomalija: [frozen.json](run01/frozen.json). Source model sa
Ledoit–Wolf matricom numerički je ponovljen, a svih 200 osnovnih AUC/pAUC
rezultata slaže se sa tačkom 1 do 1e−12. To je provjera istog polaznog modela,
ne nezavisna potvrda njegovog učinka na novom skupu.

Dodatne varijante:

- `eigen_floor_100`: svojstvene vrijednosti kovarijanse podignute najmanje
  na λmax/100; 61 smjer je ograničen.
- `diagonal_blend_010`: 0,9·C + 0,1·diag(C), poslije postojećeg Ledoit–Wolf skupljanja.
- `scale_floor_q25`: standardne devijacije ograničene na source q25 =
  0,0632678184, uz ponovno source-only Ledoit–Wolf učenje. Promijenjene su 24 komponente.

## Rangiranje

pAUC je standardizovan za FPR≤0,1. Vrijednosti su sredine preko 100 podjela.
Rasipanje i razlike svake podjele nalaze se u JSON/CSV fajlovima.

| Varijanta | AUC k=10 | pAUC k=10 | AUC k=20 | pAUC k=20 |
|---|---:|---:|---:|---:|
| Model iz tačke 1 (Ledoit–Wolf) | 0.877848 | 0.681200 | 0.882465 | 0.683737 |
| Donja granica svojstvenih vrijednosti, κ≤100 | 0.853968 | 0.652126 | 0.857525 | 0.658263 |
| 10% dodatnog dijagonalnog skupljanja | 0.865256 | 0.659642 | 0.868740 | 0.663526 |
| Donja granica standardne devijacije, q25 | 0.875524 | 0.675179 | 0.879705 | 0.677763 |

## Normalne ocjene i kalibracija

| Varijanta | Uslovljenost matrice | Srednji sirovi LOO CV, k=10 | Srednji odnos normalnog q99 i medijane, k=10 |
|---|---:|---:|---:|
| Model iz tačke 1 (Ledoit–Wolf) | 1102.48 | 0.3867 | 11.360 |
| Donja granica svojstvenih vrijednosti, κ≤100 | 100.00 | 0.3937 | 9.561 |
| 10% dodatnog dijagonalnog skupljanja | 257.10 | 0.3951 | 10.697 |
| Donja granica standardne devijacije, q25 | 1041.62 | 0.3894 | 11.447 |

Jače skupljanje smanjuje uslovljenost i ekstremne normalne ocjene, ali i
osjetljivost na anomalije. Sirovi LOO CV za k=10 nije poboljšan. Za k=20
najagresivnija varijanta smanjuje srednji CV sa 0,7082 na 0,6572, ali AUC
istovremeno pada sa 0,882465 na 0,857525. Sve matrice ostaju pozitivno
definitne poslije float32 konverzije; uslovljenost sama nije dokaz da je
postojeća matrica numerički neupotrebljiva.

`cal_raw_loo_cv` računa ocjene prema centru ostalih k−1 snimaka, prije
bilo kakvog odbacivanja. To nije konačni K1 rezultat: stvarni FW dopušta
ograničeno normal-only izostavljanje kalibracionih prozora, a postojeći
snimci ne predstavljaju fizički CAL/DERIVE/VERIFY slijed.

CSV sadrži i pomoćni prag, q99 kalibracionih ocjena, i prekoračenja na
izostavljenim normalnim snimcima. Za k=10 osnovna varijanta ima 25,88%
prekoračenja, eigen-floor 20,14%, ali odziv na anomalije pada sa 71,74%
na 61,96%. **Ovo nije FPR radnog FW-a niti simulacija GUIDED25**: mali
kalibracioni uzorak, ocjenjivanje prema sopstvenom centru, odsustvo posebne
DERIVE faze, HOLD-a i vremenskog pravila daju drugačiji postupak. Taj
pomoćni prag se nigdje ne izvozi niti zamjenjuje fizički prag uređaja.

## Dokazi i reprodukcija

- [Rezultati i razlike podjela](run01/summary.json)
- [Sve ocjene po podjeli](run01/per_split.csv)
- [Dijagnostika normalnih snimaka prije anomalija](run01/normal_only.json)
- Četiri `run01/*.npz` modela: normalizacija i matrica preciznosti.
- [Provjera hash-eva i ponavljanja osnove](verification.json)
- [Testovi numerike i eksplicitnog leave-one-out računanja](tests.txt): 2 prolaza.
- [Izvori sa originalnim bajtovima zamrznutih hash-eva](frozen_sources.zip)

Iz eksperimentalnog foldera, postojećim Python okruženjem:

```powershell
python pc/tools/evaluate_psd_covariance.py --data-root '../master new/data/dcase2026_dev' --output results/psd_covariance/ponovljeno
python -m pytest pc/tests/test_psd_covariance.py -v
```

Koriste se ranije istraživani razvojni snimci i ponovljene podjele istih
klipova. Rezultati ne procjenjuju generalizaciju na nove ventilatore.
Nema sirovog zvuka završnih fizičkih proba za ponovno izdvajanje nove PSD
mape. Nije tvrđeno da su poboljšani K1 prihvatanje, VERIFY, papirić ili oporavak.
Računarska provjera ove tri varijante je završena; njihovo uključivanje u
FW se na osnovu ovih rezultata ne predlaže.
