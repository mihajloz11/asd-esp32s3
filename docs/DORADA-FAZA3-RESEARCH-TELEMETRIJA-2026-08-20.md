# Faza 3: research telemetrija 96 + 5×96

Datum implementacije: 20.08.2026.

Status: **IMPLEMENTIRANO I PC PROVJERENO** za kod i sintetičke artefakte.
ESP-IDF clean research build je pokrenut i stigao do `1230/1519` bez greške,
ali u trenutku zatvaranja ove faze još nije bio završen; zato se build ne vodi
kao PASS dok se ne dobije završni exit code.
Stvarni sadržaj sa ventilatora ostaje **PENDING_PHYSICAL_CAPTURE**. Ova faza ne
tvrdi da su papirić i govor već razdvojeni; ona prvi put trajno čuva podatke
potrebne da se to pošteno ispita.

## 1. Zaključana granica

Kanonski PSD model nije promijenjen:

- `ASD_PSD_N_FFT=8192`, `ASD_PSD_HOP=4096`, `ASD_PSD_BANDS=96` ostaju isti;
- `asd_psd_stream_reset/push_hop/finish` ostaju produkcijski API;
- stari `asd_psd_stream_finish(out_feature)` i research finish daju
  bit-identičan finalni 96-dim vektor;
- nisu mijenjani model header, norm mean/std, precision, centar ni score;
- u DET petlji nema `asd_dump_pcm_block()` niti kontinuiranog PCM-a.

Research je zaseban, opcion build sloj. Uključuje se samo sa:

```powershell
$env:ASD_PSD_LIVE='1'
$env:ASD_RESEARCH_TELEMETRY='1'
idf.py reconfigure build
```

Bez `ASD_RESEARCH_TELEMETRY` firmware koristi stari capture/finish put i ne
emituje nove zapise.

## 2. Sidecar DSP

U `psd_features_c.h/.c` dodani su:

```c
void asd_psd_stream_reset_sidecar(void);
int asd_psd_stream_finish_sidecar(float *out_feature,
                                  asd_psd_sidecar_t *out_sidecar);
```

Sidecar drži samo `5×96` band akumulatora u statičkoj memoriji, ne PCM bafer i
ne 480 floatova na dubokom stacku. Tačno 38 preklapajućih Welch segmenata ide u
uzastopne grupe:

```text
8 + 8 + 8 + 7 + 7 = 38
```

To nisu pet nezavisnih dvosekundnih klipova. Susjedni Welch segmenti dijele
4.096 uzoraka zbog 50% preklapanja.

Sidecar sabiranje je namjerno u odvojenoj petlji poslije kanonskog `power_sum`
sabiranja. Tako ne mijenja redoslijed binary32 operacija finalnog featurea.
Podsegment i ekvivalentni batch slice se zbog drugačijeg redoslijeda band/bin
sabiranja slažu unutar `5e-5`; finalni research/canonical feature se slaže bit za
bit.

## 3. Firmware wire ugovor

Novi, odvojeni schema token je:

```text
asd-research-v1.0.0
```

Core ostaje `asd-quality-v1.4.0`, host/artifact ostaje
`physical-fan-v1.7.0`; nema lažnog bumpa kanonskog modela. Za svaki validni
CAL/DET prozor firmware emituje:

1. jedan `FEATURE96` sa session/phase/window ključem, monotonic
   `window_start_ms/window_end_ms`, scoreom, nivoom, `quality=OK`,
   `tonalness_proxy`, `dims=96`, checksumom i finalnim vektorom;
2. pet `SUBSEG96` zapisa sa istim ključem, `group=1..5`, pripadajućim brojem
   segmenata, `dims=96`, checksumom i vektorom.

Checksum je FNV-1a preko 96 little-endian binary32 vrijednosti, po istom obrascu
koji `mic_test.c` koristi za framed PCM. Decimalni zapis koristi devet značajnih
cifara, dovoljno za binary32 round-trip.

DET redoslijed je namjerno:

```text
QUALITY phase=DET ...
DET ...
FEATURE96 ...
SUBSEG96 group=1 ...
...
SUBSEG96 group=5 ...
```

Zato debug zapis ne presijeca neposredni `QUALITY DET -> DET` core ugovor.

## 4. Host strict tracker

`physical_fan_experiment.py` parsira research zapise odvojeno od core firmware
state mašine. Provjerava:

- tačan research schema token i tačan skup polja;
- `session>=1`, `window>=1`, fazu CAL/DET i `dims=96`;
- tačno 96 konačnih vrijednosti i checksum;
- `group=1..5` i broj segmenata `8/8/8/7/7`;
- `end_ms>=start_ms` i monotonic prozore;
- tačno jedan FEATURE i pet različitih SUBSEG zapisa po očekivanom validnom
  QUALITY CAL/DET prozoru;
- slaganje nivoa/tonalnosti sa QUALITY i DET scorea sa DET zapisom;
- odsustvo research zapisa između QUALITY DET i pripadajućeg DET reda.

Sa `--research-telemetry-required`, missing, duplicate, malformed, nonfinite,
checksum, shape ili korelacijska greška daje `invalid_research_telemetry`. Bez
tog flag-a core fizički rezultat ostaje odvojen: eventualni nepotpun research
sidecar je označen nevalidnim, ali ne izmišlja kvar fizičkog protokola.

Wrapper `start_fan_run.py` prosljeđuje isti flag. Ako postojeći build nema
`-DASD_RESEARCH_TELEMETRY`, required run se odbija prije otvaranja COM porta.

## 5. Artefakt

Host atomski zapisuje `window_features.npz`, zatim
`window_features.manifest.json`. NPZ sadrži:

| Array | Shape | Dtype |
|---|---:|---|
| `feature96` | `(N, 96)` | `float32` |
| `subseg96` | `(N, 5, 96)` | `float32` |
| `subseg_welch_segments` | `(N, 5)` | `int32` |
| `firmware_session_index` | `(N,)` | `int32` |
| `phase` | `(N,)` | Unicode CAL/DET |
| `window` | `(N,)` | `int32` |
| `window_start_ms`, `window_end_ms` | `(N,)` | `uint64` |
| `score`, `level_dbfs`, `tonalness_proxy` | `(N,)` | `float32` |

Manifest zapisuje shape/dtype svakog arraya i SHA-256 stvarnog NPZ fajla,
očekivani i kompletni broj prozora, broj FEATURE/SUBSEG zapisa, strict greške i
`pcm_per_det=false`.

`--wav-path` je samo veza ka fajlu nezavisnog rekordera. Manifest doslovno piše
`linked_external_file_not_recorded_by_host` i početni/završni SHA-256. Kada putanja
nije data, `external_wav=null`; host ne tvrdi da audio postoji.

## 6. Verifikacija 20.08.2026.

Ciljani testovi:

```text
.venv\Scripts\python.exe -m pytest \
  pc/tests/test_physical_fan_experiment.py \
  pc/tests/test_psd_features_c.py \
  pc/tests/test_start_fan_run.py -q

105 passed
```

Testovi eksplicitno pokrivaju bit-identičan finalni feature, `38 -> 8/8/8/7/7`,
svih `5×96` konačnih vrijednosti, batch-sidecar toleranciju, strict parser,
missing/duplicate/malformed odbijanja, NPZ shape/dtype/hash, eksterni WAV link,
DET redoslijed, odsustvo PCM poziva i sintetički UART budžet. Generisani paket
ima više od `10x` prosječne rezerve na 115200 baud i burst kraći od jedne
sekunde po desetosekundnom prozoru.

## 7. Šta ostaje za naredni stvarni test

- flashovati research build i potvrditi stvarne FEATURE/SUBSEG linije na COM-u;
- snimiti mali broj dobro označenih normal/govor/papirić prozora;
- provjeriti stvarni UART burst i `dropped_delta=0` na uređaju;
- po želji paralelno snimati eksterni WAV i proslijediti njegovu putanju;
- tek iz novih NPZ podataka analizirati koje trake i podsegmenti razdvajaju govor
  od trajne promjene ventilatora.

Nije potrebno ponavljati mnogo puta prije ove provjere. Jedan kratak, uredno
označen research run je dovoljan da prvo potvrdimo da instrumentacija radi i da
li signal za razdvajanje uopšte postoji.
