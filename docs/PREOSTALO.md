# Preostali rad

Ažurirano 06.09.2026. Posljednji firmware ostaje zamrznut. Dodatna fizička
mjerenja nisu planirana u ovom završnom ciklusu; neprovjerena svojstva
navode se kao ograničenja, bez obećanja naknadnih rezultata.

## Završeno

- pregled izvora, protokola, rezultata i oba rada;
- ponovljene host provjere: 478 prošlo, provjera šeme prošla;
- rezultati završnih proba ponovo izračunati uz jedinstven izbor prozora;
- razdvojeni validna telemetrija, prolaz kalibracije i ishod probe;
- sačuvani izvorni firmware, modeli i sirovi mjerni zapisi.

Detalji: [revizija projekta](../results/repository_audit/2026-09-06/README.md).

## Prije predaje i javne objave

| Stavka | Gdje se rješava |
|---|---|
| Komisija, potpisi, izjava, mentorov pregled i uslov publikacije | [master](../radovi/master-rad/PREOSTALO-RAD.md) |
| Koautorski pregled, copyright oznaka i PDF eXpress | [TELFOR](../radovi/telfor2026/PREOSTALO-RAD.md) |
| Prava na šablone, privatni podaci i licenca sopstvenog koda | [revizija](../results/repository_audit/2026-09-06/README.md) |

## Neprovjerena svojstva

Samostalan sklop sa fizičkim tasterom i LED, prekid I2S veze, nestanak
napajanja, potrošnja cijelog detektora, dug normalan rad i nova akustička
postavka nisu potvrđeni završnim probama. DEVELOPMENT politika ne čuva
profil u NVS; nakon restarta slijedi novo učenje. Postojeći storage testovi
nisu dokaz rada pri fizičkom prekidu napajanja.

## Moguća poboljšanja

Prioritet je [provjera praznih PSD traka](../results/repository_audit/2026-09-06/gain_probe.json)
i uticaja kovarijanse, zatim rubni slučajevi audio konverzije i pouzdanost
brojača gubitaka. Prijedlozi su u
[problemima i rješenjima](problemi-i-rjesenja.md#p28--revizija-pred-objavu-06092026).
To su budući eksperimenti; nijedna nova politika nije uključena u radni firmware.
