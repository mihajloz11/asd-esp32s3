# Dorada Faze 1 — K1 fail-closed ugovor

**Datum:** 16.08.2026.  
**Commissioning politika:** `asd-commissioning-policy-v1.0.0`.  
**Novi live UART:** `asd-quality-v1.4.0`.  
**Novi host artefakti:** `physical-fan-v1.7.0`.

## Šta je promijenjeno

- Jedini PC numerički izvor ostaje
  `pc/config/asd_commissioning_policy_v1.json`: `loo_cv <= 0,6` prolazi.
- Firmware kopiju istog verzionisanog pravila sprovodi čisti, host-testabilni
  `asd_calibration_quality.c/.h`; parity test poredi njen prag i policy ID sa
  JSON zapisom.
- K1 se primjenjuje nad istom vrijednošću `loo_cv` zaokruženom na šest decimala
  koja ulazi u `CAL_SUMMARY`. Time binary32 ULP na samoj granici ne može dati
  različitu odluku na uređaju i hostu.
- `psd_live.c` izvršava K1 odmah poslije `CAL_SUMMARY`. Pad emituje postojeći
  terminalni `STATE`/`FLOW_STOPPED` par sa razlogom
  `UNSTABLE_CALIBRATION` i vraća se prije `ADAPTTHR`,
  `CALIBRATION_ACCEPTED` i DET petlje.
- Host parser nezavisno potvrđuje da je primljeni `loo_cv` zaista iznad K1
  granice. Takav kraj je validan protokol sa odbijenom kalibracijom, ali nikad
  rezultat podoban za metrike. `ADAPTTHR` ili `CALIBRATION_ACCEPTED` poslije
  pada K1 tretiraju se kao nevalidna firmware telemetrija.

## Kompatibilnost starih artefakata

Novi live capture zahtijeva `asd-quality-v1.4.0` i piše
`physical-fan-v1.7.0`. Stari UART nije tiho prihvaćen kao novi live ugovor.

Offline `recompute` namjerno nastavlja čitati postojeće
`physical-fan-v1.6.0` run direktorijume nastale uz `asd-quality-v1.3.0`.
Čitanje koristi sačuvani `firmware_protocol_state` i centralnu K1 politiku;
originalni `SUMMARY.md`, `provenance.json`, CSV i UART zapisi se ne mijenjaju.
Korekcija smije nastati samo kao novi sidecar.

Stvarni istorijski `cold-start-04` zato ostaje netaknut, a read-only
rekomputacija ga ispravno klasifikuje kao
`calibration_rejected:loo_cv_above_max` i `Validan fizički rezultat: NE`.

## Granica dokaza

Host-C testovi, literalni UART replay i ESP-IDF build dokazuju implementaciju i
integraciju bez hardvera. Tek flash i stvarni UART replay potvrđuju ponašanje
konkretne pločice; build sam po sebi nije runtime dokaz.
