# Poglavlje 2 — Pregled stanja u oblasti (draft)

> Draft za master rad. Materijal iz plana (sekcija 2) + rezultati projekta.
> Reference u [plan-master-rada.md](../planovi/plan-master-rada.md) sekcija 12.

## 2.1 Detekcija anomalija zvuka (ASD) — definicija problema

Detekcija anomalija zvuka mašina (engl. *Anomalous Sound Detection*, ASD) bavi
se prepoznavanjem odstupanja u akustičnom potpisu mašine koja ukazuju na kvar
ili degradaciju. Za razliku od klasične klasifikacije kvarova, ASD se formuliše
kao **nenadgledani** problem: u treningu su dostupni isključivo zvuci normalnog
rada, a sistem mora prepoznati bilo koje odstupanje — uključujući tipove kvarova
koji nisu viđeni tokom obuke. Ovakva postavka odražava industrijsku realnost:
kvarovi su rijetki, raznovrsni i teško se unaprijed prikupljaju u dovoljnom
broju za nadgledano učenje.

## 2.2 DCASE Challenge Task 2 (2020–2026)

DCASE (*Detection and Classification of Acoustic Scenes and Events*) Challenge
uspostavio je Task 2 kao referentni okvir za ASD. Kroz godine, zadatak je
sistematski usložnjavan:

| Godina | Fokus | Doprinos okviru |
|---|---|---|
| 2020 | Nenadgledani ASD | Definicija problema, AE baseline, log-mel front-end |
| 2021 | Domain shift | Adaptacija na promjenu uslova rada |
| 2022 | Domain generalization | Isti prag za source i target domen; MIMII DG, ToyADMOS2 |
| 2023 | First-shot | Potpuno novi tipovi mašina |
| 2024 | Skriveni atributi | AE baseline sa MSE i Mahalanobis modovima |
| 2025 | First-shot nastavak | — |
| 2026 | Noise-aware, dvokanalni | Parovi blizu/daleko mikrofona |

**Zvanični baseline** (koji ovaj rad preuzima kao referentnu metodologiju)
zasniva se na autoenkoderu nad log-mel spektrogramom: STFT sa prozorom od 64 ms,
128 mel filtera, konkatenacija 5 uzastopnih frejmova u ulazni vektor dimenzije
640. Anomaly score je greška rekonstrukcije (MSE mod) ili Mahalanobisova
distanca rekonstrukcionih grešaka (MAHALA mod). Prag odlučivanja fituje se
gamma raspodjelom na score-ovima normalnih klipova (90. percentil), pri čemu se
prag nikada ne tunira na test skupu.

**Metrike:** AUC odvojeno za source i target domen, pAUC pri niskom FPR (≤ 0.1),
zvanični skor kao harmonijska sredina. Harmonijska sredina nemilosrdno kažnjava
loš rezultat na bilo kojoj komponenti, čime se sprečava da model dobar samo na
jednom domenu prođe kao uspješan.

## 2.3 Jače metode iznad baseline-a

Od 2022. dominiraju pristupi zasnovani na samonadgledanoj klasifikaciji sekcija
mašine uz *embedding* backend (kNN, Mahalanobis ili GMM nad naučenim
reprezentacijama): STgram-MFN sa ArcFace gubitkom, kontrastivno predtreniranje
(CLP-SCF), interpolacioni autoenkoderi (IDNN), Glow-bazirani modeli. Ključan
zaključak iz literature, relevantan za izbor u ovom radu, jeste da **nijedna
arhitektura ne dominira na svim tipovima mašina** — što opravdava izbor
jednostavnog, deployabilnog autoenkodera kao osnove za resursno ograničenu
implementaciju.

## 2.4 TinyML deployment — direktna konkurencija i rupa u literaturi

| Rad | Urađeno | Ograničenje (rupa) |
|---|---|---|
| AE TinyML na Cortex-M4 | Real-time AE na industrijskom zvuku | Bez DCASE protokola, bez domain-shift evaluacije |
| OutlierNets | Ekstremno kompaktni conv-AE (2.7 KB) | Deploy na Core i5/Cortex-A72 — nije MCU klasa |
| LSTM-AE na ESP32 | ESP32 deploy, kvantizacija | Urbani šum, ne mašine; bez DCASE metrika |
| ArrythML (ESP32-S3, TFLM) | Metodološki šablon za S3 deploy | EKG domen |

**Formulacija rupe:** postoje (a) DCASE ASD metode evaluirane na GPU i (b)
ad-hoc TinyML audio deploymenti bez DCASE rigora. Ne postoji sistematska studija
koja DCASE protokol (domain shift, AUC/pAUC) spušta na mikrokontroler klase
uz izmjeren resursni budžet (memorija, latencija, energija). Ovaj rad zatvara
tu rupu.

## 2.5 Pozicioniranje ovog rada

Rad kombinuje DCASE-standardnu ML evaluaciju sa embedded implementacijom na
ESP32-S3 i klasičnom ESP32, mjerećи Pareto kompromis tačnost ↔ memorija ↔
latencija ↔ energija, efekat int8 kvantizacije po tipu mašine, i efekat SIMD
(PIE) instrukcija na identičnom kodu. Doprinos je empirijski: kvantitativna
karta koliko DCASE-klase ASD sistema "staje" u dati resursni budžet.
