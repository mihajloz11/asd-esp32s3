# Konačni cilj modela

Ovo je obavezni pravac projekta i kriterij za sve naredne odluke o modelu.

1. Na računaru se uči opšti oblik **normalnog rada ventilatora** iz velikog
   korpusa dobrih snimaka više ispravnih ventilatora. Anomalni snimci nisu
   potrebni za obuku konačnog detektora.
2. Dobijeni mali model/statistički opis prilagođava se ograničenjima
   ESP32-S3 i ugrađuje u firmware.
3. Pri prvom postavljanju pored novog ventilatora pločica nekoliko minuta sluša
   njegov potvrđeno ispravan rad i lokalno kalibriše centar, normalne radne
   režime i prag. Taj ventilator nije morao biti u korpusu za učenje.
4. Poslije kalibracije ESP32-S3 radi **potpuno samostalno, bez računara**:
   obrađuje zvuk, računa anomaly score, prepoznaje odstupanje u oba smjera i
   označava alarm (serijski ispis, LED, a kasnije po potrebi mrežna poruka).
5. Kalibracija se ne smije tiho nastaviti tokom sumnjivog rada, jer bi uređaj
   mogao naučiti kvar kao normalno stanje. Ponovna kalibracija mora biti
   svjesno pokrenuta i urađena samo na potvrđeno ispravnom ventilatoru.

## Mjerljivi cilj

- Istraživački cilj: **AUC najmanje 0,80 na novom ventilatoru** uz pošten
  protokol bez curenja podataka.
- AUC 0,50 je slučajno rangiranje; AUC 0,60 je slab signal, ali ne znači
  "60 % tačnosti". AUC mjeri koliko dobro score rangira anomalne iznad
  normalnih primjera kroz sve moguće pragove.
- Za stvarni uređaj AUC nije dovoljan. Nakon izbora praga obavezno se prijavljuju
  i odziv na kvarove, broj lažnih alarma i kašnjenje detekcije.
- Ako 0,80 nije dostignuto, prijavljuje se najbolji ponovljiv rezultat bez
  uljepšavanja i jasno se razdvaja DCASE benchmark od testa sa stvarnim kvarom.

## Pravilo poštenog mjerenja

Klipovi korišteni za učenje opšteg modela, lokalnu kalibraciju i konačnu ocjenu
moraju biti razdvojeni. Ciljne anomalije smiju se koristiti samo za konačnu
ocjenu, nikad za računanje centra, kovarijanse, praga ili izbor varijante koja
će se proglasiti konačnom.
