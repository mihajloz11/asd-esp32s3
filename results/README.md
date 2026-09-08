# Mapa rezultata

Putanje mjerenja ostaju nepromijenjene jer na njih upućuju skripte,
metapodaci i radovi. Neuspjeli pokušaji čuvaju se uz uspješne.

| Grupa | Upotreba |
|---|---|
| [fw_followup/2026-09-07](fw_followup/2026-09-07/README.md) | zajednički pregled četiri probe, grana, FW paketa i završnih provjera |
| [physical_fan](physical_fan/) | serijski zapisi, oznake uslova, ocjene, izvještaji i porijeklo fizičkih proba |
| [repository_audit/2026-09-06](repository_audit/2026-09-06/README.md) | revizija, hash inventar, provjera brojki i dokumenata |
| [psd_nonempty/2026-09-07](psd_nonempty/2026-09-07/README.md) | eksperimentalne neprazne trake: bolje razvojno rangiranje i zaseban FW; još bez fizičke probe |
| [audio_hardening/2026-09-07](audio_hardening/2026-09-07/README.md) | tačke 2 i 3: zasićenje uzoraka, sinhronizacija statistike, zasebni FW paketi; 490 testova prolazi |
| [psd_covariance/2026-09-07](psd_covariance/2026-09-07/README.md) | tačka 4: tri dodatne varijante nisu poboljšale model iz tačke 1 |
| [advanced](advanced/) | alternativna obilježja i pravila odlučivanja |
| `results.csv`, tabele i grafikoni u ovom direktorijumu | razvojne evaluacije; protokol se čita uz konkretan artefakt |

## Završne fizičke probe

| Proba | Izvor | Tumačenje |
|---|---|---|
| Papirić, 27.08. | [run A](physical_fan/run_20260827T213148_fan02_guided25-20260827-v3recovery5d/) | validna telemetrija i prihvaćena kalibracija; GUIDED25 FAIL |
| Ton od 1 kHz, 27.08. | [run B](physical_fan/run_20260827T220338_fan02_tone-validation-20260827-final/) | validna telemetrija, alarm i trajno odstupanje; završni oporavak nije izmjeren |

Sažeci u radovima koriste samo `protocol_valid=1`, `condition_confirmed=1`
i `transition_window=0`. HOLD prozori ostaju u metrikama. To daje 43/65
i 99/115 DET prozora. Grafikoni prikazuju i ostale DET zapise radi kontinuiteta.
Stari generisani sažeci ostaju izvorni artefakti; za ispravljeno tumačenje
koristiti [pregled proba](../docs/rezultat-finalna-validacija-2026-08-27.md).

Razvojni AUC, simulacija vremenskog pravila, PC–C poređenje, replay i fizička
proba predstavljaju različite vrste dokaza. Njihove brojeve ne treba spajati
u jednu procjenu tačnosti. Originalni DCASE audio i veliki keševi nisu u Gitu.
