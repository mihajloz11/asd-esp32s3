# Audio konverzija i dijagnostika

## Tačka 2 — zasićenje audio uzoraka

Grana `codex/audio-sample-saturation` polazi od završene neprazne PSD mape.
Zaseban paket čuva stanje poslije ove tačke, prije sinhronizacije brojača.
Originalni radni firmware i prvi PSD paket nisu prepisani.

Konverzija je izdvojena u `audio_pcm.h`. Skaliranje 1/16384 i zaokruživanje
negativnih uzoraka nadolje ostaju isti. Vrijednosti van int16 opsega sada
se zasićuju na −32768/32767. Apsolutna vrijednost računa se preko int64,
a sirovi peak vraća uint32 da može tačno predstaviti i 2147483648.
Poziv u `mic_test.c` usklađen je sa tim tipom.

Provjereno je 262144 uzoraka koji pokrivaju svaki int16 bin, 100000
slučajnih int32 vrijednosti i 17 rubnih vrijednosti. C test ima uključeno
hvatanje signed overflow-a (`-ftrapv`). Prvi pokušaj učitavanja test DLL-a
tražio je GCC runtime; statičko povezivanje libgcc riješilo je zavisnost.
Nije bilo numeričkog pada. Završno: **22 testa prolaze**, ESP-IDF build prolazi.

- [Testovi](step2_tests.txt)
- [Build](step2_build.txt)
- [Manifest paketa](step2_firmware.json)
- Paket: `dist/audio-saturation-2026-09-07`, candidate i originalni rollback.
- Aplikacija: 355184 B, SHA-256 `a7ccd93704c4a26b1632950829fcaee88f851a7221c2169feb63b57899c129b3`.

Za male signale rezultat je identičan dosadašnjem. Kod zasićenja je
namjerno drugačiji i omogućava postojećoj provjeri kvaliteta da vidi
klipovanje. Ovo nije izmjereno poboljšanje akustičkog detektora.
Uređaj nije flešovan; fizička provjera i vrijeme računanja ostaju otvoreni.

## Tačka 3 — sinhronizacija statistike

Grana `codex/audio-statistics-sync` nastavlja tačku 2. Modul `audio_stats.c`
čuva brojače, peak i status iza jednog ESP-IDF `portMUX` zaključavanja.
Kritične sekcije sadrže samo kratke upise/čitanja; nijedna ne obuhvata
I2S, ring-buffer poziv, konverziju uzoraka ili čekanje. Peak se objavljuje
jednom po obrađenom bloku umjesto zaključavanja za svaki uzorak.

Reset `dropped` ostaje na kraju početnog pražnjenja bafera. Granica je
trenutak zaključanog reseta: upis gubitka poslije nje ostaje vidljiv, čak
ako je iz proizvođačkog bloka započetog prije reseta. To može konzervativno
pripisati takav gubitak novoj sesiji; ne potiskuje ga da bi proba prošla.
Peak ima granicu objavljivanja bloka, ne preciznu granicu pojedinačnog uzorka.
Unsigned 32-bit brojači zadržavaju postojeću wrap-around semantiku.

Četiri testa konkurentnosti pozivaju stvarni C modul iz više host niti.
Host zamjenjuje samo FreeRTOS zaključavanje sistemskim mutexom; time se
provjeravaju dijeljeni podaci, a ne raspoređivanje stvarnog ESP32 RTOS-a.
40.000 upisa po 1024 uzorka uz 10.000 reseta sačuvalo je tačan zbir
40.960.000. Dodatno su provjereni peak/reset, 40.000 istovremenih prijava
grešaka i 20.000 snimaka statusa naspram upisa heartbeat/count para.

Ciljani skup: **26 prolaza**. Puna regresija sa kompletnim podacima:
**490 prolaza, bez preskakanja**, 37,82 s. ESP-IDF build prolazi.

- [Ciljani testovi](step3_tests.txt), [puna regresija](full_tests.txt)
- [Build](step3_build.txt), [manifest](step3_firmware.json)
- Paket: `dist/audio-stats-sync-2026-09-07`, candidate i originalni rollback.
- Aplikacija: 355328 B, SHA-256 `612b8b70aa69ff8e611c6c17108a7829da21306264133ccefe6f42b7b3bc884d`.

Ovaj paket sadrži tačke 1, 2 i 3. Paket tačke 1 ostaje prvi izbor za
izolovanu fizičku provjeru nove PSD mape. Ne mijenjati pakete usred mjerenja.
Prije fizičkog snimanja lokalni build koji host koristi za porijeklo mora
odgovarati tačno flešovanom paketu; ne pokretati host iz starog repoa sa
novim binom. Nijedan paket nije flešovan u ovoj sesiji.
