# Od zvuka do alarma — vodič kroz naš projekat

Za razumijevanje i razgovor sa profesorom. Provjereno prema kodu i zapisima ovog repozitorijuma 23.09.2026. Finalni tok je **ASD_PSD_LIVE**, uz istraživačku telemetriju korišćenu u završnim probama. Istorijski eksperimenti nijesu svi dio tog toka.

## 1. Prvo napravi jednu sliku u glavi

**Ventilator pravi zvuk → mikrofon daje brojeve → izdvajamo oblik spektra → poredimo ga sa normalnim radom → provjeravamo pouzdanost i trajanje promjene → alarm.**

Ne tražimo unaprijed snimljen zvuk svakog mogućeg kvara. Učimo kako izgleda normalan rad i pitamo: „Koliko se ovo što sada čujem razlikuje od normale?” To je detekcija anomalija. Veliko odstupanje ne govori samo po sebi koji dio mašine je pokvaren.

Četiri riječi će se stalno ponavljati: **spektar** je prikaz frekvencija u zvuku; **obilježje / feature** je broj izračunat iz zvuka, npr. snaga u jednoj traci; **otisak / vektor** je lista tih brojeva za jedan snimak; **skor / score** je jedan broj koji govori koliko je taj otisak neobičan. Dakle: mnogo uzoraka zvuka → 96 brojeva opisa → jedan skor za odluku.

Najbrže učenje: prvo pročitaj odjeljke 1–8 i ispričaj put signala svojim riječima. Zatim 9–13 za model i odluku. Tek onda pogledaj istoriju i dokaze. Kod otvaraj uz pojam koji upravo učiš, ne čitaj cijeli firmware odjednom. Poslije svakog odjeljka zatvori tekst i odgovori na njegovo pitanje.

**Za profesora:** „Implementirao sam samostalni detektor promjene zvuka ventilatora. Spektralna obilježja i Mahalanobisov skor računaju se na ESP32-S3; lokalna kalibracija prilagođava model konkretnoj postavci.”


<!-- BEGIN KEY CODE -->
Zvuk · **→** I2S / PCM · **→** Welch / 96 brojeva · **→** Skor · **→** Pouzdano i trajno? · **→** Alarm

### Ključni kod: Ulaz u samostalni PSD tok

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\app_main.c`

**Redovi:** 169–178. Doslovni isječak; okolni kod je izostavljen.

```c
#if defined(ASD_PSD_LIVE) || defined(ASD_PSD_VERIFY)
    ESP_ERROR_CHECK(audio_i2s_init());
    ESP_ERROR_CHECK(audio_i2s_start());
#ifdef ASD_PSD_VERIFY
    psd_verify_run();
#else
    psd_live_run();
#endif
    while (1) vTaskDelay(portMAX_DELAY);
#endif
```
<!-- END KEY CODE -->
## 2. I2S, mikrofon i PCM — tri različite stvari

**Mikrofon INMP441** pretvara promjene zvučnog pritiska u digitalni audio. **I2S** je način prenosa tog digitalnog zvuka do ESP32. **PCM** je niz brojeva koji predstavlja amplitudu zvuka kroz vrijeme. Pretpostavljam da si pod „pmc” mislio na PCM.

Zamisli dostavu: mikrofon pravi podatke, I2S ih donosi, PCM je sadržaj paketa. I2S nije FFT, model niti frekvencija zvuka.

**Amplituda** je trenutna vrijednost talasa — koliko je iznad ili ispod svoje nule. **Frekvencija** je koliko puta se talas ponovi u sekundi. Veća amplituda iste sinusoide znači jači ton; veća frekvencija znači viši ton. Jedan PCM broj govori samo o jednom trenutku; frekvenciju prepoznajemo tek iz niza brojeva.

Tri glavne žice:

| Signal | Šta radi | ESP32-S3 pin |
|---|---|---|
| BCLK | takt za prenos pojedinačnih bitova | GPIO4 |
| WS | označava lijevi/desni audio slot | GPIO5 |
| SD → DIN | prenosi same audio podatke ka ESP32 | GPIO6 |

ESP32 je ovdje master: daje taktove. L/R na mikrofonu je vezan na GND, pa čitamo lijevi slot. **16 kHz je broj uzoraka u sekundi, ne brzina svakog bita na BCLK žici.** Uzorak stiže svakih 62,5 mikrosekundi. WS ciklus odgovara frekvenciji uzorkovanja; BCLK je brži jer prenosi mnogo bitova po okviru.

**Gdje smo konfigurisali:** `firmware/esp32s3_asd/main/audio_i2s.h` definiše `AUDIO_SR = 16000`; `pins.h` definiše pinove; `audio_i2s.c`, funkcija `audio_i2s_init()`, postavlja takt, Philips I2S format, 32-bitni slot i mono prijem. `audio_i2s_start()` uključuje prijem. `app_main.c` bira PSD tok i pokreće audio.

**Slot** je mjesto predviđeno za jedan podatak u prenosu. Kao kutija sa 32 mjesta za bitove: INMP441 u njoj šalje 24-bitni podatak, pa veličina kutije nije rezolucija mjerenja. U `capture_task()` radimo `pcm[i - off] = (int16_t)(raw[i] >> 14);`: `>> 14` pomjera bitove udesno, a `(int16_t)` rezultat pretvara u 16-bitni cijeli broj. To je konkretno skaliranje naše implementacije, nije univerzalno pravilo za I2S mikrofone. Pretvaranje tipa ne ograničava automatski prevelik broj na dozvoljeni maksimum; pri prejakoj amplitudi može doći do prekoračenja. Kasniji audio-hardening, odnosno dodatna zaštita audio ulaza, zaseban je eksperiment.

**DMA** pomaže da periferija prenosi blokove podataka bez ručnog čitanja svakog bita procesorom. **Ring buffer** je kružni red: snimanje dodaje uzorke, obrada ih uzima. Kapacitet je dvije sekunde 16-bitnog mono zvuka, oko 64 kB. Nalazi se u `audio_i2s.c`. Prva sekunda poslije pokretanja odbacuje se zbog ustaljivanja mikrofona.

PCM je, recimo, `[0, 100, 180, 100, 0, -100, ...]`. To još nijesu frekvencije. U `psd_live.c`, `capture_clip()`, brojevi se dijele sa `32768.0f` da dobijemo float približno u opsegu −1 do 1.

**Provjeri sebe:** Ko pravi podatke, ko ih prenosi, a kako se zove niz amplituda?


<!-- BEGIN KEY CODE -->
### Kako talas postaje niz brojeva

Pritisni „Sljedeći uzorak”. Svaka tačka je jedno očitavanje amplitude. Pokreni animaciju da vidiš kako se niz puni.

Sljedeći uzorak · Pokreni animaciju · Vrati na početak

**Zapamti:** PCM pamti visinu talasa u trenucima uzorkovanja, a ne spisak frekvencija.

Usporena ilustracija: 16 tačaka po periodi izmišljenog talasa. Naš mikrofon daje 16000 uzoraka u sekundi. Prikazane amplitude su normalizovane, nijesu sirovi I2S bitovi.

### Ključni kod: Frekvencija uzorkovanja i kapacitet bafera

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\audio_i2s.h`

**Redovi:** 13–18. Doslovni isječak; okolni kod je izostavljen.

```c
#define AUDIO_RING_SEC   2                       /* ring buffer kapacitet */
#define AUDIO_RING_LEN   (AUDIO_SR * AUDIO_RING_SEC)
#define AUDIO_READ_DEFAULT_TIMEOUT_MS 2000u
#define AUDIO_I2S_CAPTURE_WAIT_MS      250u

typedef struct {
```

### Ključni kod: I2S: takt, format, pinovi i lijevi slot

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\audio_i2s.c`

**Redovi:** 129–153. Doslovni isječak; okolni kod je izostavljen.

```c
            .bclk = PIN_I2S_BCLK,
            .ws = PIN_I2S_WS,
            .dout = I2S_GPIO_UNUSED,
            .din = PIN_I2S_DIN,
        },
    };
    /* INMP441 L/R na GND -> podaci u lijevom slotu */
    std_cfg.slot_cfg.slot_mask = I2S_STD_SLOT_LEFT;
    ESP_ERROR_CHECK(i2s_channel_init_std_mode(rx_chan, &std_cfg));
    return ESP_OK;
}

esp_err_t audio_i2s_start(void) {
    ESP_ERROR_CHECK(i2s_channel_enable(rx_chan));
    BaseType_t ok = xTaskCreatePinnedToCore(capture_task, "audio_cap", 4096, NULL,
                                            configMAX_PRIORITIES - 2, NULL, 0);
    return ok == pdPASS ? ESP_OK : ESP_FAIL;
}

esp_err_t audio_read_exact(int16_t *dst, size_t n_samples,
                           uint32_t timeout_ms, size_t *samples_read) {
    if (samples_read) *samples_read = 0;
    if (!dst || !samples_read || n_samples == 0 || timeout_ms == 0 || !ring)
        return ESP_ERR_INVALID_ARG;

```

### Ključni kod: Prenos u 16-bitni PCM i ring buffer

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\audio_i2s.c`

**Redovi:** 96–107. Doslovni isječak; okolni kod je izostavljen.

```c
        }
        size_t out = n - off;
        if (xRingbufferSend(ring, pcm, out * sizeof(int16_t), 0) != pdTRUE)
            dropped += out;
    }
}

esp_err_t audio_i2s_init(void) {
    /* Ring buffer: PSRAM ako postoji, inače interni SRAM (2 s @ 16 kHz 16-bit
     * = 64 KB — staje i na klasični ESP32). DMA baferi drajvera ostaju u
     * internom SRAM-u u oba slučaja (S3 DMA ne vidi PSRAM). */
    static StaticRingbuffer_t rb_struct;
```

### Ključni kod: PCM amplituda postaje float

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_live.c`

**Redovi:** 489–491. Doslovni isječak; okolni kod je izostavljen.

```c
        for (int i = 0; i < HOP; i++) {
            hop[i] = (float)pcm[i] / 32768.0f;
        }
```
<!-- END KEY CODE -->
## 3. Nyquist — zašto 16 kHz ne znači zvuk do 16 kHz

Mikrofon ne čuva neprekidnu liniju talasa, nego vrijednosti u odabranim trenucima. Ako je talas prebrz između dva očitavanja, može se provući dio njegovih promjena koji nijesmo vidjeli. Tada različiti tonovi mogu dati isti niz uzoraka i računar ih više ne može razlikovati. Zato uzorkujemo brže od **dvostruke najviše frekvencije koju želimo sačuvati**, a više frekvencije moraju biti dovoljno potisnute prije uzorkovanja.

Za `fs = 16000 Hz`, Nyquistova granica je **8000 Hz**. U praksi ne oslanjamo se na tačno graničnu frekvenciju. Analogni ton iznad te granice, ako nije dovoljno potisnut prije uzorkovanja, može izgledati kao niži ton: to je **aliasing**. Primjer idealnog uzorkovanja: 10 kHz može se preslikati na 6 kHz pri 16 kHz uzorkovanju.

**Gdje je u kodu?** Nema funkcije `nyquist()`. Granica slijedi iz `AUDIO_SR`; u spektru realnog signala C petlja ide do `ASD_PSD_N_FFT / 2`. Model zatim bira samo opseg **10–4000 Hz**. Taj izbor nije anti-alias filter: odbacivanje FFT binova poslije uzorkovanja ne može popraviti već nastali aliasing. Digitalni mikrofon ima svoj interni audio lanac; u ovom firmwareu nijesmo implementirali analogni filter ispred njegovog konvertora.

**Za profesora:** „Uzorkujem sa 16 kHz, teorijska Nyquistova granica je 8 kHz, a iz spektra za model izdvajam opseg 10–4000 Hz.”

**Provjeri sebe:** Da li su 4 kHz, 8 kHz i 16 kHz ovdje ista vrsta granice?


<!-- BEGIN KEY CODE -->
### Nyquist: isti uzorci mogu skrivati drugi ton

Izaberi ton. Plava linija je originalni idealni kosinus; tačke su uzorci pri 16 kHz. Iznad granice se pojavljuje narandžasti ton sa istim uzorcima.

Ton · 2 kHz · 6 kHz · 10 kHz · 14 kHz

**Zapamti:** Kada uzorci već izgledaju isto, FFT ne može pogoditi koji je originalni ton bio prisutan.

Matematička ilustracija idealnog uzorkovanja, bez anti-alias filtriranja. Ne simulira interni filter INMP441 mikrofona.

### Ključni kod: Jednostrani spektar: binovi do N/2

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 91–92. Doslovni isječak; okolni kod je izostavljen.

```c
    psd_fft();
    for (int bin = 0; bin <= ASD_PSD_N_FFT / 2; bin++)
```
<!-- END KEY CODE -->
## 4. FFT i broj 8192

PCM govori **kako se amplituda mijenja kroz vrijeme**. FFT računa **koje frekvencijske komponente postoje i koliko su izražene**. Kao kada iz zvuka akorda pokušavaš izdvojiti pojedinačne tonove. FFT je brz algoritam za diskretnu Furijeovu transformaciju.

`N` je broj stvarnih uzoraka u jednom FFT segmentu, odnosno komadu snimka koji zajedno obrađujemo. Kod nas je **8192 = 2¹³**. Koristimo radix-2 FFT: postupak razlaže račun na manje dijelove prepolovljavanjem, pa mu odgovara dužina koja je stepen dvojke. Implementiran je u `psd_features_c.c`, funkcija `psd_fft()`. Broj nije magičan niti je dokazano da je globalno najbolji od svih mogućih N.

| FFT dužina | Trajanje segmenta pri 16 kHz | Razmak FFT binova fs/N |
|---|---|---|
| 1024, raniji mel tok | 64 ms | 15,625 Hz |
| 8192, finalni PSD tok | 512 ms | 1,953125 Hz |

**Bin** je jedna frekvencijska tačka FFT izlaza. Duži stvarni segment omogućava finiji frekvencijski opis, ali promjenu gledaš preko dužeg vremena. Razmak binova nije garancija da ćeš svaki par tonova udaljen 1,95 Hz razdvojiti: Hann prozor i šum takođe određuju stvarnu razlučivost. Samo dodavanje nula kratkom segmentu ne daje istu dodatnu informaciju kao 8192 stvarna uzorka.

Zamisli binove kao oznake na frekvencijskom lenjiru: kod nas su na 0 Hz, 1,953 Hz, 3,906 Hz i tako dalje. Finije oznake pomažu da vidiš sitnije razlike. Ali ako se zvuk promijeni usred segmenta od 0,512 s, taj FFT opisuje i dio prije i dio poslije promjene — zato slabije govori **tačno kada** se ona desila.

Zašto je pomoglo našem projektu? Rotacija i ponavljajući prolazak lopatica često stvaraju tonske komponente i harmonike. Primjer za razumijevanje: 1800 obrtaja/min znači 30 obrtaja/s; pet lopatica daje frekvenciju prolaska lopatica oko 150 Hz. To nije izmjerena brzina našeg ventilatora. Promjena rada može promijeniti jačine tih komponenti, harmonike, bočne komponente ili šum.

**Harmonici** su komponente na cjelobrojnim umnošcima neke osnovne frekvencije: uz 150 Hz mogu se javiti 300, 450 Hz… **Bočne komponente** su dodatni vrhovi pored glavnog, koji se mogu pojaviti kada se, recimo, jačina zvuka periodično mijenja. Njihovo prisustvo samo po sebi ne dokazuje kvar; poredimo ih sa normalnim radom.

Raniji FFT 1024 plus mel sažimanje mogao je izgubiti fine spektralne razlike. Novi frontend koristi duži FFT i drugačije trake, a bolji razvojni rezultat podržava taj izbor. **Nijesmo izolovanim testom dokazali da je samo promjena N izazvala sav dobitak:** promijenjen je cijeli opis zvuka.

**Gdje:** konstante su u `psd_features_c.h`; C FFT u `psd_features_c.c`; Python referenca je `pc/tools/bench_periodicity.py`, `periodic_features()`.

**Provjeri sebe:** Zašto ne stavimo beskonačno veliki N?


<!-- BEGIN KEY CODE -->
### PCM → prozor → FFT: prođi kroz jedan račun

**8192 je broj uzoraka koji zajedno ulaze u jedan FFT.** Nije frekvencija, broj sekundi ni broj traka modela. Ovdje računamo stvarni FFT izmišljenog zvuka sastavljenog od tonova 100 i 110 Hz.

Prethodni korak · Sljedeći korak · Pokreni animaciju · Počni ponovo

**Dvije upotrebe riječi prozor:** vremenski prozor je izabranih 8192 uzorka; Hann prozor je lista 8192 težine kojima ih množimo. FFT zatim dobija tih 8192 umnožaka.

Primjer koristi 16 kHz i periodični Hann kao projekat. FFT radi u JavaScriptu sa decimalnim brojevima; ovo nije izvršavanje C firmvera niti novo mjerenje ventilatora. Brojevi PCM-a prikazani su kao normalizovani float.

### Pojedinačno: snimak, Hann i njihov proizvod

Sve tri slike imaju istu vremensku osu: cijelih 512 ms. Pomjeri uzorak od ruba do sredine i gledaj zašto ga Hann na različitim mjestima različito umanjuje.

Indeks uzorka n

**Ulaz u FFT je treća slika.** Hann nije novi snimljeni zvuk, nego unaprijed izračunata lista težina. U sredini težina iznosi 1, pa tamo uzorak ostaje isti.

Linije su radi preglednosti nacrtane pomoću 801 tačke. Račun koristi svih 8192 uzorka. Označena tačka i ispis koriste tačan izabrani uzorak, ne samo tačke crteža.

### Zumiraj jedan bin: šta tačno stoji u njemu?

Pomjeraj bin oko dvije komponente. **Bin je jedno mjesto u FFT rezultatu**, označeno indeksom `k`. Uz njega je vezana frekvencija `k × 16000 / 8192`. Narandžasti stub je izabrani bin.

Indeks bina k

**Zapamti:** jedan ulazni PCM broj pripada jednom trenutku. Jedan izlazni FFT bin opisuje jednu frekvencijsku tačku koristeći **svih 8192 ulazna uzorka**. Nema pravila „prvi uzorak postaje prvi bin”.

Za bin k algoritam sabira doprinose cijelog segmenta, poredeći ih sa sinusom i kosinusom te frekvencije. Ako signal sadrži sličnu komponentu, doprinosi se manje poništavaju i bin ima veću amplitudu. FFT je brz način da se taj račun uradi za sve binove.

Prikazujemo skaliranu snagu (Re² + Im²), kao za jedan Hann segment u našem spektru snage. Bin nije savršen pravougaoni filter: ton može doprinijeti i susjednim binovima. Sa realnim ulazom od 8192 uzorka imamo 4097 nenegativnih binova, k=0…4096, do 8000 Hz.

### Zašto 8192: ista dva tona, duže posmatranje

Oba računa koriste isti sintetički zvuk, 16 kHz i Hann. Mijenja se samo broj stvarnih uzoraka. Izaberi jedan ton, pa dva bliska tona.

Zvuk · 100 Hz + 110 Hz · Samo 100 Hz

**1024:** 64 ms zvuka, binovi na 15,625 Hz. **8192:** 512 ms zvuka, binovi na 1,953 Hz. Duži snimak pomaže razlikovanju bliskih tonova, ali opis obuhvata duži dio vremena.

**Veza sa našim izborom:** ventilator ima ponavljajuće tonske komponente. Finiji spektralni opis pomogao je ispitivanom PSD pristupu, a račun je stao na ESP32. Broj 8192 je i stepen dvojke, pogodan za naš FFT. Ovo poređenje objašnjava kompromis; ne dokazuje da je 8192 najbolji za svaki zvuk, niti da je samo N donio sav razvojni dobitak.

Oba grafa imaju istu skalu frekvencije i snage. Isprekidane oznake su stvarne frekvencije sintetisanih tonova. Hann širi vrhove, pa razmak binova nije isto što i garantovana razlučivost. Trake vremena ispod pokazuju dužine posmatranja, ne izmjereno kašnjenje alarma.

### Promijeni N, a uzorkovanje ostaje 16 kHz

Dužina FFT-a · 1024 · 2048 · 4096 · 8192 · 16384

Tačke su FFT binovi u opsegu 100–200 Hz. Gušće tačke znače finiji razmak; ovo nije simulacija razdvajanja dva tona.

**Tekst koraka animacije:**

- 1 / 4 · PCM: niz amplituda po vremenu. Ispod je uvećano prvih 160 uzoraka (10 ms). To je samo mali dio ulaza, ne cijelih 8192.

- 2 / 4 · Izdvoji 8192 uzorka, od indeksa 0 do 8191. Oni pokrivaju 512 ms pri 16000 uzoraka/s. Svaki uzorak čeka svoje mjesto u FFT ulazu.

- 3 / 4 · Primijeni Hann: x[n] × w[n]. Rubovi se utišavaju, sredina zadržava punu težinu. To smanjuje problem naglog spoja kraja i početka segmenta.

- 4 / 4 · FFT mijenja opis: sa amplituda kroz vrijeme prelazimo na kompleksne vrijednosti po frekvenciji. Iz njih računamo snagu i crtamo binove. Ovdje vidiš samo opseg 60–150 Hz.

### Ključni kod: Tri glavne konstante

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.h`

**Redovi:** 7–9. Doslovni isječak; okolni kod je izostavljen.

```c

#define ASD_PSD_N_FFT 8192
#define ASD_PSD_HOP 4096
```

### Ključni kod: Stvarni radix-2 FFT

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 25–49. Doslovni isječak; okolni kod je izostavljen.

```c
static void psd_fft(void) {
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        int j = bitrev[i];
        if (j > i) {
            float t = fft_re[i]; fft_re[i] = fft_re[j]; fft_re[j] = t;
            t = fft_im[i]; fft_im[i] = fft_im[j]; fft_im[j] = t;
        }
    }
    for (int len = 2; len <= ASD_PSD_N_FFT; len <<= 1) {
        int half = len >> 1;
        int step = ASD_PSD_N_FFT / len;
        for (int i = 0; i < ASD_PSD_N_FFT; i += len) {
            for (int k = 0; k < half; k++) {
                float wr = tw_re[k * step], wi = tw_im[k * step];
                int a = i + k, b = a + half;
                float xr = fft_re[b] * wr - fft_im[b] * wi;
                float xi = fft_re[b] * wi + fft_im[b] * wr;
                fft_re[b] = fft_re[a] - xr;
                fft_im[b] = fft_im[a] - xi;
                fft_re[a] += xr;
                fft_im[a] += xi;
            }
        }
    }
}
```
<!-- END KEY CODE -->
## 5. Hann i 50% preklapanja — ne izbacujemo rubove

FFT dobija odsječen segment, a njegov frekvencijski opis odgovara ponavljanju tog segmenta. Zamisli da isti mali snimak puštaš u krug: ako se kraj i početak ne poklapaju, na spoju se pojavi skok kojeg u izvornom zvuku možda nije bilo. Zbog tog spoja jedan ton može u rezultatu izgledati raširen po više frekvencija — to je **spektralno curenje**. Hann ublažava spoj tako što smanjuje vrijednosti blizu krajeva segmenta.

Svaki uzorak pomnožimo brojem od 0 do 1: `novi_uzorak = stari_uzorak × Hann_težina`. Ne biramo samo srednju trećinu, ne tražimo „pravi centralni signal” i ne brišemo pola snimka. Ublažavanje rubova plaćamo širenjem spektralnog vrha.

Na primjer, uzorak 100 sa težinom 0,1 postaje 10, a sa težinom 1 ostaje 100. „Težina” ovdje samo znači koliko ga umanjimo. „Širenje vrha” znači da prikaz jednog tona postaje širi, pa dva bliska tona može biti teže razdvojiti.

```text
blokovi od 4096 uzoraka:  [ A ][ B ][ C ][ D ] ...
FFT segment 1:           [ A    B ]
FFT segment 2:                [ B    C ]
FFT segment 3:                     [ C    D ]
```

Segment traje 8192 uzorka, a pomjeramo se za **4096**: to je 50% preklapanja. Blok B učestvuje u dva FFT-a. Ono što je blizu ruba jednog segmenta bolje je zastupljeno u susjednom segmentu. Za periodični Hann, težine dva ovako pomjerena prozora u zajedničkom području dopunjuju se do 1. **Ali naš algoritam ne rekonstruiše signal sabiranjem tih prozora:** računa i prosječi spektre snage. Zato tu osobinu koristi kao intuiciju o pokrivenosti, ne kao dokaz savršene rekonstrukcije.

Krajnji rubovi cijelog snimka nemaju sve susjede; preklapanje nije čarobno potpuno uklanjanje rubnih efekata.

**Gdje:** `asd_psd_init()` pravi Hann niz; `psd_accumulate_segment()` množi uzorke tim nizom; `asd_psd_stream_push_hop()` pravi segment od prethodnog i tekućeg hopa. Sve je u `psd_features_c.c`.

**Provjeri sebe:** Ako je B već korišćen, zašto ga opet koristimo?


<!-- BEGIN KEY CODE -->
### Isti uzorak, dvije različite težine

Položaj uzorka u zajedničkom dijelu

Plavo: segment [A B]. Narandžasto: segment [B C]. Mijenjaj položaj uzorka i gledaj kako se težine dopunjuju. Za Welch prosječimo snage, ne sabiramo prozore da vratimo originalni signal.

### Ključni kod: Pravljenje Hann težina

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 51–67. Doslovni isječak; okolni kod je izostavljen.

```c
void asd_psd_init(void) {
    int log2n = 0;
    while ((1 << log2n) < ASD_PSD_N_FFT) log2n++;
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        double a = -2.0 * M_PI * (double)i / (double)ASD_PSD_N_FFT;
        if (i < ASD_PSD_N_FFT / 2) {
            tw_re[i] = (float)cos(a);
            tw_im[i] = (float)sin(a);
        }
        hann[i] = (float)(0.5 - 0.5 * cos(2.0 * M_PI * (double)i /
                                        (double)ASD_PSD_N_FFT));
        unsigned r = 0;
        for (int b = 0; b < log2n; b++)
            if ((unsigned)i & (1u << b)) r |= 1u << (log2n - 1 - b);
        bitrev[i] = (uint16_t)r;
    }

```

### Ključni kod: Prethodni + tekući hop

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 209–223. Doslovni isječak; okolni kod je izostavljen.

```c
int asd_psd_stream_push_hop(const float *hop) {
    int done = 0;
    if (stream_have_prev) {
        /* prozor = [prethodni hop | tekuci hop] */
        for (int i = 0; i < ASD_PSD_HOP; i++) fft_re[i] = stream_prev[i];
        for (int i = 0; i < ASD_PSD_HOP; i++) fft_re[ASD_PSD_HOP + i] = hop[i];
        psd_accumulate_segment();
        if (stream_sidecar_enabled) sidecar_accumulate_segment(stream_segments);
        stream_segments++;
        done = 1;
    }
    memcpy(stream_prev, hop, sizeof(stream_prev));
    stream_have_prev = 1;
    return done;
}
```
<!-- END KEY CODE -->
## 6. STFT, Welch i PSD — razvrstaj ih ovako

**STFT:** više FFT-ova kroz vrijeme. Svaki kratki segment daje svoj spektar. Kad ih poslažeš dobiješ spektrogram: vrijeme × frekvencija, boja pokazuje jačinu. Raniji log-mel tok računa `stft_power()` u `pc/asd/features.py`.

**Welch:** podijeli signal na preklopljene segmente, pomnoži uzorke svakog segmenta Hann težinama, izračunaj njegov spektar snage i prosječi rezultate. Ako isti bin u tri segmenta ima snagu 2, 5 i 2, njegov prosjek je 3. Tako pojedinačno kolebanje manje utiče na konačni prikaz. STFT čuva „kakav je spektar bio u kom trenutku”, a Welch daje „kakav je spektar u prosjeku tokom snimka”. Iz samog prosjeka više ne znaš kada se koji događaj desio.

**PSD**, power spectral density, pokazuje **gdje se po frekvenciji nalazi snaga zvuka**. Na grafiku je vodoravno frekvencija, a uspravno spektralna gustina snage. Visok vrh oko 100 Hz znači da je komponenta oko 100 Hz izražena; ne znači da je zvuk nastao u stotoj sekundi. Snaga je povezana sa kvadratom amplitude: duplo veća amplituda istog tona daje četiri puta veću snagu.

„Gustina” znači da snagu izražavamo po jedinici frekvencije, odnosno po Hz, da možemo porediti različito široke opsege. **Preciznost za naš kod:** tok zovemo PSD, ali `scaling="spectrum"` računa spektar snage, ne gustinu po Hz. C prati tu istu postavku. Radimo sa digitalnim vrijednostima; nijesmo ih kalibrisali u fizičke jedinice zvučnog pritiska.

FFT za svaki bin daje dva broja, `real` i `imag`, koji zajedno opisuju jačinu i fazu komponente. Za snagu koristimo `real² + imag²`, pa ne moraš prvo savladati kompleksne brojeve da pratiš ovaj korak. Za realne PCM uzorke negativna polovina spektra ponavlja istu informaciju o snazi, pa čuvamo samo nenegativnu polovinu — **jednostrani spektar**. `psd_finalize()` prosječi i pravilno skalira te vrijednosti.

**Tri vremenska nivoa koje moraš razlikovati:**

| Šta | Veličina | Svrha |
|---|---|---|
| FFT segment | 8192 uzorka = 0,512 s | jedan spektar |
| Hop | 4096 uzoraka = 0,256 s | pomjeraj do sljedećeg segmenta |
| Prozor za jednu odluku | 39 hopova = 159744 uzorka = 9,984 s | 38 FFT segmenata → jedan otisak od 96 brojeva |

Ne računamo FFT dužine 160000. Računamo 38 manjih preklopljenih FFT-ova i prosječimo. Zato tri uzastopna prozora alarma znače oko 30 s posmatranja, ne tri puta 0,512 s. Stvarno kašnjenje od nastanka promjene zavisi i od njenog položaja u prozoru, HOLD-a i ostalog toka; nije izmjereno samo množenjem.

**Gdje:** `HOPS_PER_CLIP` i `capture_clip()` u `psd_live.c`; Welch koraci u `psd_features_c.c`.


<!-- BEGIN KEY CODE -->
### PSD: jedan pomiješan zvuk, dvije frekvencije

Pomjeraj jačinu komponente od 300 Hz. Istovremeno gledaj oblik talasa lijevo i raspored snage desno.

Amplituda tona 300 Hz · Pokreni animaciju

**Zapamti:** Lijevo pitaš „kako se zvuk mijenja kroz vrijeme?”, desno „gdje mu je snaga po frekvenciji?”.

Idealna suma sinusoida od 100 i 300 Hz. Desno je teorijska srednja snaga A²/2 svake komponente, a ne rezultat FFT-a ili stvarno mjerenje. Stvarni konačni prozori daju šire vrhove.

### Welch: više spektara → jedan prosjek

Dodaj spektar sljedećeg segmenta. Siva linija pokazuje trenutni segment; plava prosjek svih do sada dodatih segmenata.

Dodaj sljedeći segment · Pokreni animaciju · Vrati na početak

**Zapamti:** Ponavljajuća struktura ostaje u prosjeku; promjenljiva kolebanja se ublažavaju.

Sintetički spektri za prikaz prosječenja, bez izračunavanja FFT-a. U projektu prosječimo 38 preklopljenih segmenata; oni nijesu nezavisni. Prosjek ne garantuje uklanjanje svake buke.

### Ključni kod: Hann → FFT → snaga

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 86–94. Doslovni isječak; okolni kod je izostavljen.

```c
static void psd_accumulate_segment(void) {
    for (int i = 0; i < ASD_PSD_N_FFT; i++) {
        fft_re[i] *= hann[i];
        fft_im[i] = 0.0f;
    }
    psd_fft();
    for (int bin = 0; bin <= ASD_PSD_N_FFT / 2; bin++)
        power_sum[bin] += fft_re[bin] * fft_re[bin] + fft_im[bin] * fft_im[bin];
}
```

### Ključni kod: STFT: poseban spektar za svaki frejm — istorijski frontend

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\asd\features.py`

**Redovi:** 51–56. Doslovni isječak; okolni kod je izostavljen.

```python
    n_frames = 1 + (len(y) - n_fft) // hop
    win = hann_window(n_fft)
    idx = np.arange(n_fft)[None, :] + hop * np.arange(n_frames)[:, None]
    frames = y[idx] * win[None, :]
    spec = np.fft.rfft(frames, n=n_fft, axis=1)
    return (np.abs(spec) ** 2).astype(np.float32)
```

### Ključni kod: Welch i 96 traka — finalni frontend

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\tools\bench_periodicity.py`

**Redovi:** 56–58. Doslovni isječak; okolni kod je izostavljen.

```python
    f, p = welch(y, fs=SR, window="hann", nperseg=8192, noverlap=4096,
                 detrend=False, scaling="spectrum")
    psd = _band_log_power(f, p, np.geomspace(10.0, 4000.0, 97))
```
<!-- END KEY CODE -->
## 7. Mel trake naspram naših 96 traka

Zamisli hiljade FFT vrijednosti kao mnogo uskih posuda. Trake ih sakupljaju u manji broj sažetih vrijednosti.

**Mel trake** su najčešće preklopljeni trougaoni filteri: jedna frekvencija može doprinositi susjednim trakama različitim težinama. Raspored je prilagođen ljudskom opažanju visine tona: više detalja na nižim, šire grupisanje na višim frekvencijama. Poslije logaritmovanja dobija se log-mel. To je koristan opis zvuka, ali nije automatski najbolji za svaku mašinu.

„Filter” ovdje znači račun nad FFT brojevima: binove blizu sredine trake više uračunamo, a one blizu ruba manje. Trougao na slici predstavlja te težine, ne oblik samog zvuka. **Frontend** je naziv za cijeli dio koji od uzoraka pravi takav opis; **frejm** je jedan kratki vremenski segment.

Raniji frontend: FFT 1024, 128 mel traka, slaganje pet frejmova → vektor 640. Mapa mel težina pravi se u `pc/asd/features.py`, a C istorijski frontend je `features_c.c`.

**Finalni frontend nije mel.** Pravi 96 intervala sa logaritamski raspoređenim granicama između 10 i 4000 Hz. Granice rastu istim odnosom, pa su niže trake uže. Prosječimo snagu FFT binova u svakom intervalu, pa uzmemo log10. Logaritamski raspored frekvencijskih granica i logaritmovanje snage su dvije različite operacije.

Za raspored granica zamisli 10, 20, 40, 80 Hz: svaki put množiš istim brojem, umjesto da dodaješ isti broj herca. To je samo primjer, ne naše stvarne granice. **Log10 snage** ima drugu svrhu: vrijednosti 1, 10 i 100 pretvara u 0, 1 i 2. Tako vrlo velike i male snage dobijaju pregledniju skalu; snaga manja od 1 može imati negativan logaritam, ali nije negativna snaga.

U fizički korišćenoj verziji **8 od 96 intervala nema FFT bin** i dobija vrijednost −20 prije centriranja. Zaseban kasniji kandidat to ispravlja; on nije verzija fizičkih završnih proba. Zbog ovih praznih traka ni uklanjanje uticaja ukupne jačine nije savršeno.

**Gdje:** `_band_log_power()` i `np.geomspace(...)` u `bench_periodicity.py`; `band_start`, `band_len` i `psd_finalize()` u C. Kasniji eksperiment: `results/psd_nonempty/2026-09-07/README.md`.

**Provjeri sebe:** Da li 96 traka znači da imamo 96 mikrofona ili 96 opisa istog zvuka?


<!-- BEGIN KEY CODE -->


### Ključni kod: STFT snaga → mel filteri → logaritam — istorijski frontend

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\asd\features.py`

**Redovi:** 63–65. Doslovni isječak; okolni kod je izostavljen.

```python
    p = stft_power(y)
    mel = p @ mel_filterbank().T
    return ((20.0 / POWER) * np.log10(mel + LOG_EPS)).astype(np.float32)
```

### Ključni kod: Srednja snaga u logaritamskim intervalima — finalni frontend

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\tools\bench_periodicity.py`

**Redovi:** 40–45. Doslovni isječak; okolni kod je izostavljen.

```python
def _band_log_power(freq: np.ndarray, power: np.ndarray, edges: np.ndarray) -> np.ndarray:
    out = []
    for lo, hi in zip(edges[:-1], edges[1:]):
        mask = (freq >= lo) & (freq < hi)
        out.append(np.log10(float(power[mask].mean()) + 1e-20) if np.any(mask) else -20.0)
    return np.asarray(out, np.float64)
```

![Mel filteri i PSD intervali — konceptualna šema](mel-i-psd-trake.svg)

*Mel filteri i PSD intervali — konceptualna šema.*
<!-- END KEY CODE -->
## 8. Šta je psd_shape i zašto uklanjamo nivo

Poslije računanja traka imamo 96 brojeva. Od svakog oduzmemo **jednu zajedničku srednju vrijednost svih 96 brojeva**. Tako naglašavamo oblik: koje trake su relativno jače ili slabije.

Primjer: `[2, 4, 6]` ima sredinu 4 i postaje `[-2, 0, 2]`. `[5, 7, 9]` ima sredinu 7 i postaje isto. Zajednički pomak je nestao, oblik je ostao. To je intuitivni razlog za manju osjetljivost na ukupnu glasnoću. U stvarnom baselineu postoje ograničenja zbog praznih traka, poda i promjene odnosa signal/šum.

Tri slična računa imaju različitu svrhu:

| Račun | Šta konkretno uklanja ili mijenja |
|---|---|
| Oduzimanje sredine PCM uzoraka | Ako talas osciluje oko 100 umjesto oko nule, oduzmemo 100. Taj stalni pomak zove se DC komponenta. |
| Oduzimanje sredine 96 log-traka | U jednom snimku uklanjamo zajednički nivo traka da naglasimo njihov međusobni odnos. To je `psd_shape`. |
| Standardizacija svake trake | Upoređujemo je sa njenom tipičnom vrijednošću i rasipanjem kroz mnogo normalnih snimaka. Primjer je u odjeljku 10. |

**Gdje:** posljednja petlja u `psd_finalize()`; Python `psd - psd.mean()`.


<!-- BEGIN KEY CODE -->
### Glasnije nije isto što i drugačiji oblik

Mijenjaj zajedničku jačinu ili uključi promjenu jedne trake. Desno se od svake vrijednosti oduzima zajednička sredina.

Zajednički log-pomak · Promijeni samo treću traku

**Zapamti:** Zajednički pomak nestaje centriranjem. Promjena odnosa među trakama ostaje.

Četiri izmišljene log-vrijednosti umjesto 96. Idealizovano, bez praznih traka i poda; u fizički korišćenom baselineu otpornost na glasnoću nije savršena.

### Ključni kod: Prosjek snage, logaritam i uklanjanje nivoa

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 100–121. Doslovni isječak; okolni kod je izostavljen.

```c
static int psd_finalize(int segments, float *out_feature) {
    if (segments <= 0) return 0;
    const float win_sum = (float)ASD_PSD_N_FFT * 0.5f;
    const float scale = 2.0f / ((float)segments * win_sum * win_sum);
    float feature_mean = 0.0f;
    for (int band = 0; band < ASD_PSD_BANDS; band++) {
        int count = band_len[band];
        if (count == 0) {
            out_feature[band] = -20.0f;
        } else {
            float sum = 0.0f;
            int first = band_start[band];
            for (int i = 0; i < count; i++) sum += power_sum[first + i];
            float mean_power = scale * sum / (float)count;
            out_feature[band] = log10f(mean_power + 1e-20f);
        }
        feature_mean += out_feature[band];
    }
    feature_mean /= (float)ASD_PSD_BANDS;
    for (int band = 0; band < ASD_PSD_BANDS; band++) out_feature[band] -= feature_mean;
    return segments;
}
```
<!-- END KEY CODE -->
## 9. Euklidska udaljenost, varijansa i kovarijansa

Svaki približno 10-sekundni snimak daje listu od 96 brojeva. Matematički je zovemo „tačka u prostoru od 96 dimenzija”, ali ne moraš zamišljati prostor koji ne možemo nacrtati. Uzmi samo dvije trake: ako su njihove vrijednosti 2 i 5, taj snimak nacrtaj kao tačku `(2,5)`. Sljedeći snimak daje drugu tačku. Mnogo normalnih snimaka tako pravi **oblak tačaka**; stvarni model isti princip primjenjuje na svih 96 vrijednosti.

**Euklidska udaljenost** je obična udaljenost lenjirom. Od normale `(0,0)`, tačke `(3,3)` i `(3,-3)` jednako su udaljene. Ali šta ako normalan rad prirodno povećava obje trake zajedno? Tada `(3,3)` može biti uobičajeno, a `(3,-3)` neobično.

**Varijansa** kaže koliko jedna veličina normalno varira. **Standardna devijacija** je njen korijen, u istim jedinicama kao ta veličina. **Kovarijansa** kaže kako dvije veličine variraju zajedno: pozitivna kada obično rastu zajedno, negativna kada jedna raste dok druga pada. Ne dokazuje uzročnost.

Konkretno: traka sa vrijednostima 9, 10 i 11 malo varira, a traka sa 2, 10 i 18 mnogo više. Ako se u istim snimcima dvije trake ponašaju kao `(1,2)`, `(2,4)`, `(3,6)`, rastu zajedno. Model pamti tu vezu, pa bi kombinacija `(3,1)` bila neobičnija nego da su obje porasle kao inače.

**Matrica kovarijanse** je tabela tih odnosa. Na dijagonali su varijanse, van dijagonale veze parova. Kod nas je 96 × 96. **Korelacija** je srodna, normalizovana mjera veze; nije ista numerička veličina kao kovarijansa.

Oblak normalnih tačaka može biti izdužen ukoso. Običan lenjir taj oblik ignoriše. Nama treba udaljenost koja pita: „Da li je ovo odstupanje veliko u odnosu na način na koji normalan zvuk inače varira?”


<!-- BEGIN KEY CODE -->
### Isti lenjir, različita neobičnost

Koliko snažno trake rastu zajedno

Ilustrativne dvije dimenzije, nije mjerenje našeg ventilatora. Matrica je [[1, ρ], [ρ, 1]]. Elipsa označava isti Mahalanobisov skor 4. Prikazane tačke imaju istu euklidsku udaljenost od centra.
<!-- END KEY CODE -->
## 10. Mahalanobis i Ledoit–Wolf

**Mahalanobisova udaljenost** pita: „Koliko je ova promjena neobična u odnosu na normalne promjene?” Ako jedna traka u normalnom radu često odstupa za 10, pomak od 3 nije naročit. Ako druga obično odstupa samo za 0,2, pomak od 3 je velik. Uz to se gleda da li se trake mijenjaju zajedno kao inače. Zato dvije jednako udaljene tačke na običnom grafiku mogu dobiti različit skor.

Naš skor je **kvadrirana** Mahalanobisova udaljenost:

```text
z = (feature - source_mean) / source_std
delta = z - local_center
score = deltaᵀ × precision × delta
precision = inverzna matrica regularizovane kovarijanse
```

Prva linija je **standardizacija**: ako traka normalno ima sredinu 10 i standardnu devijaciju 2, izmjerenih 14 postaje `(14−10)/2 = 2`. To znači „dvije standardne devijacije iznad uobičajene vrijednosti”. Račun se radi za svaku traku posebno. `local_center` je tipična lista takvih vrijednosti za naš konkretni ventilator; `delta` govori koliko je novi snimak udaljen od te liste.

`precision` je tabela težina izvedena iz kovarijanse: njome račun uzima u obzir koje promjene su uobičajene i kako su povezane. `ᵀ` samo okreće kolonu u red radi množenja. Rezultat je jedan skor; veći znači neobičniji otisak, ne veću dokazanu vjerovatnoću kvara. Korijen se ne računa jer ne mijenja redosljed skorova, a prag postavljamo u istoj kvadriranoj skali.

**Ledoit–Wolf** sprečava da model previše vjeruje vezama procijenjenim iz ograničenog broja snimaka. Recimo da su se dvije trake u našim podacima skoro savršeno kretale zajedno. Običan račun mogao bi zaključiti da je i najmanje razilaženje veoma neobično, iako je ta gotovo savršena veza djelimično slučajna. Tada mala promjena daje pretjerano veliki skor.

Postupak zato malo ublaži izmjerene veze i ekstremno mala rasipanja. **Regularizacija** je naziv za takvo sprečavanje pretjeranog oslanjanja na nesigurnu procjenu. Precizno, izmjerenu kovarijansu miješa sa jednostavnijom tabelom koja ima jednaku varijansu za sve dimenzije i nule van dijagonale — skaliranom jediničnom matricom. Koliko ih miješa procjenjuje iz podataka. Veze se ublažavaju, ne moraju nestati; loš opis zvuka time ipak ne postaje automatski dobar.

**Gdje treniramo:** `pc/tools/gen_psd_model_header.py`, `main()`: 990 normalnih source snimaka → sredine i standardne devijacije → `LedoitWolf().fit(normalized).precision_`. Izvozi `models/fan_psd_shape.npz`, metapodatke i `firmware/esp32s3_asd/main/psd_model_data.h`.

**Gdje izvršavamo:** `asd_psd_score()` u `psd_features_c.c`. Uređaj koristi izvezenu matricu; ne trenira Ledoit–Wolf uživo. Sama float32 matrica ima 96 × 96 × 4 = 36864 bajta. To je mali statistički model, bez neuronske mreže.

**Provjeri sebe:** Zašto ista udaljenost od centra ne mora značiti istu neobičnost?


<!-- BEGIN KEY CODE -->
### Ledoit–Wolf: ublaži nesigurne veze

Pomjeraj jačinu skupljanja. Izdužena elipsa postepeno postaje pravilnija: vrlo uski smjer više ne dobija ekstremnu težinu.

Ilustrativno skupljanje

**Zapamti:** Skupljanje stabilizuje procjenu kovarijanse. Ne uči gdje je kvar.

Dvodimenzionalni primjer: (1 − α) × kovarijansa + α × I, sa varijansama 1. U pravom Ledoit–Wolf postupku α se procjenjuje iz podataka; ne bira se ovim klizačem.

### Ključni kod: Standardizacija i Ledoit–Wolf na normalnim podacima

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\tools\gen_psd_model_header.py`

**Redovi:** 59–72. Doslovni isječak; okolni kod je izostavljen.

```python
        raise ValueError(f"očekivano (990,{DIM}), dobijeno {source.shape}")

    mean = source.mean(axis=0)
    std = source.std(axis=0) + 1e-8
    normalized = (source - mean) / std
    precision = LedoitWolf().fit(normalized).precision_

    mean32 = mean.astype(np.float32)
    std32 = std.astype(np.float32)
    precision32 = precision.astype(np.float32)
    checksum = digest(mean32, std32, precision32)

    NPZ_OUT.parent.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(NPZ_OUT, mean=mean32, std=std32, precision=precision32)
```

### Ključni kod: C funkcija za Mahalanobisov skor

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_features_c.c`

**Redovi:** 245–261. Doslovni isječak; okolni kod je izostavljen.

```c
float asd_psd_score(const float *feature, const float *norm_mean,
                    const float *norm_std, const float *precision,
                    const float *local_center, int dim) {
    static float delta[ASD_PSD_BANDS];
    static float projected[ASD_PSD_BANDS];
    if (dim > ASD_PSD_BANDS) return NAN;
    for (int i = 0; i < dim; i++)
        delta[i] = (feature[i] - norm_mean[i]) / norm_std[i] - local_center[i];
    for (int i = 0; i < dim; i++) {
        float sum = 0.0f;
        for (int j = 0; j < dim; j++) sum += precision[i * dim + j] * delta[j];
        projected[i] = sum;
    }
    float score = 0.0f;
    for (int i = 0; i < dim; i++) score += delta[i] * projected[i];
    return score;
}
```
<!-- END KEY CODE -->
## 11. Šta se uči na PC-u, a šta na ventilatoru

**PC:** mnogo normalnih source snimaka uči opšti oblik varijacija i skalu obilježja. **ESP32:** normalni zvuk konkretne postavke uči lokalni centar i pragove. Drugi ventilator, prostorija i položaj mikrofona mogu pomjeriti tipičan otisak — to je dio problema promjene domena.

**Source** su raniji snimci iz kojih učimo opšti model; **target** je novi ventilator/postavka na kojoj ga provjeravamo. **Lokalni centar** nije fizičko mjesto mikrofona: to je prosječna lista obilježja normalnog zvuka te postavke. **Prag** je granica dozvoljenog skora. Centar odgovara na „šta je ovdje tipično?”, a prag na „koliko odstupanje ćemo tolerisati?”.

Finalna procedura nije samo „deset prozora pa odmah alarm”:

1. **WAIT/ustaljivanje:** provjera da audio i izvor imaju smisla.
2. **CAL:** deset približno 10-sekundnih normalnih prozora za centar i stabilnost. K1 pravilo može odbaciti najviše dva najgora klipa; preostali moraju zadovoljiti provjeru stabilnosti. Centar je sredina prihvaćenih standardizovanih obilježja, ne medijana.
3. **DERIVE:** zasebni normalni prozori za pragove. U završnim zapisima ima ih 44. Ulazni prag izvodi se empirijskim p99 pravilom.
4. **VERIFY:** zasebna provjera na normalnom radu; u završnim zapisima 22 prozora. Loša kalibracija može biti odbijena.
5. **DET:** centar i pragovi ostaju zamrznuti; ocjenjujemo novi zvuk.

**Percentil p99** je visoka vrijednost u izmjerenoj normalnoj raspodjeli. Sa 44 prozora i korišćenim „higher” izborom p99 je maksimum tih 44 vrijednosti. To nije garancija 1% budućih lažnih alarma.

**LOO**, leave-one-out: kad provjeravamo kalibracioni klip, njegov centar računamo bez tog klipa, da on sam sebi ne smanji odstupanje. **CV** je odnos standardne devijacije i sredine skorova; ovdje služi provjeri stabilnosti kalibracije. Stariji dokumenti imaju ranije pragove p90 ili sredina+3σ; to nijesu konačna pravila završnih sesija.

Zašto ne prilagođavamo centar stalno? Zato što bi uređaj postepeni kvar mogao naučiti kao novu normalu. Zašto ne učimo na papiriću i govoru? Zato što želimo normal-only kalibraciju; ciljane anomalije služe ocjeni nakon zamrzavanja pravila.

**Gdje:** `psd_live.c`, CAL petlje, LOO, `COMMISSION_ENTER_QUANTILE`, DERIVE/VERIFY; `asd_profile_runtime.c` zamrzava profil; `asd_calibration_quality.c` provjerava kvalitet kalibracije. Za pregled toka kreni od `psd_live.c`, a ne od hiljada brojeva u zaglavlju modela.


<!-- BEGIN KEY CODE -->


### Ključni kod: Početni CAL centar prije moguće K1 korekcije

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_live.c`

**Redovi:** 820–825. Doslovni isječak; okolni kod je izostavljen.

```c
    for (int d = 0; d < DIM; d++) {
        float s = 0.0f;
        for (int i = 0; i < N_CAL; i++)
            s += (cal_feat[i][d] - asd_psd_norm_mean[d]) / asd_psd_norm_std[d];
        center[d] = s / (float)N_CAL;
    }
```

### Ključni kod: LOO centar bez klipa koji ocjenjujemo

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_live.c`

**Redovi:** 829–836. Doslovni isječak; okolni kod je izostavljen.

```c
    float loo[N_CAL];
    for (int i = 0; i < N_CAL; i++) {
        float c[DIM];
        for (int d = 0; d < DIM; d++) {
            float zi = (cal_feat[i][d] - asd_psd_norm_mean[d]) / asd_psd_norm_std[d];
            c[d] = (center[d] * (float)N_CAL - zi) / (float)(N_CAL - 1);
        }
        loo[i] = score_with_center(cal_feat[i], c);
```

### Ključni kod: Ulazni i izlazni percentil — prije ograničenja izlaznog praga

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\psd_live.c`

**Redovi:** 1047–1057. Doslovni isječak; okolni kod je izostavljen.

```c
    float derive_sorted[MAX_COMMISSION_WINDOWS];
    memcpy(derive_sorted, derive_scores,
           commissioning.policy.derive_windows * sizeof(float));
    threshold_enter = percentile_higher(
        derive_sorted, (int)commissioning.policy.derive_windows,
        COMMISSION_ENTER_QUANTILE);
    memcpy(derive_sorted, derive_scores,
           commissioning.policy.derive_windows * sizeof(float));
    threshold_exit = percentile_higher(
        derive_sorted, (int)commissioning.policy.derive_windows,
        COMMISSION_EXIT_QUANTILE);
```

![Šta uči PC, a šta ESP32](pc-i-esp32-ucenje.svg)

*Šta uči PC, a šta ESP32.*
<!-- END KEY CODE -->
## 12. Tri prozora, histereza i HOLD

**Tri uzastopna pouzdana prekoračenja** smanjuju osjetljivost na pojedinačan kratki skok. `asd_temporal.c` definiše `DEFAULT_MIN_CONSECUTIVE 3`; `asd_temporal_update()` povećava brojač iznad ulaznog praga i resetuje ga kada uslov nije ispunjen.

```text
skor/prag:  1,2   1,3   0,8   1,1   1,4   1,2
brojač:       1     2     0     1     2     3 → alarm
```

**Histereza** znači da je prag za povratak niži od praga za ulaz. Time se izbjegava paljenje/gašenje oko iste granice. Završni `psd_live.c` izvodi apsolutne pragove iz normalnih DERIVE podataka: izlaz polazi od p95, ograničen je polovinom ulaznog praga i medijanom normale; nevažeća kombinacija odbija se. Nemoj završni tok opisivati samo starim podrazumijevanim odnosom 0,7 iz `asd_temporal.c`.

Primjer sa izmišljenim pragovima 100 i 50: tri pouzdana skora iznad 100 pale alarm. Kada alarm već traje, pad na 80 ga ne gasi; treba pasti na 50 ili niže. Tako malo kolebanje oko 100 ne pali i gasi lampicu stalno. **Medijana** u pravilu iznad znači srednju vrijednost po položaju kada brojeve poređamo od najmanjeg do najvećeg.

**HOLD** znači „ovo posmatranje nije dovoljno pouzdano za takvu odluku”. U svakom približno 10-sekundnom prozoru pratimo pet grupa Welch segmenata, raspoređenih 8/8/8/7/7. Računamo koliko se njihovi standardizovani spektralni opisi mijenjaju. To nijesu pet potpuno nezavisnih snimaka jer su segmenti preklopljeni.

Zamisli dva snimka sa istim visokim ukupnim skorom. U prvom se sličan neobičan zvuk čuje kroz svih deset sekundi. U drugom prvo čuješ ventilator, zatim kratak govor, pa opet ventilator: opis se jako mijenja unutar snimka. Provjera nestabilnosti pokušava da prepozna upravo takvu razliku. Ne zna da je u pitanju govor — vidi samo veliku promjenljivost.

Ako je skor visok i nestabilnost prevelika, HOLD zaustavlja gradnju novog alarma. Granica nestabilnosti izvodi se u toj sesiji kao najveća CAL nestabilnost × 1,25. Govor i vrata ne određuju tu granicu. Ako alarm već traje, HOLD ga ne briše automatski; pauzira pouzdano brojanje. Sljedeći stabilan niz mora ponovo ispuniti pravilo.

**Nijesmo razdvojili izvore zvuka.** Jedan mikrofon čuje zbir ventilatora i okoline. HOLD prepoznaje određenu nepouzdanost, ne porijeklo zvuka. Stabilan spoljni ton može podići alarm, a nestabilna promjena ventilatora može završiti u HOLD-u. Upravo zato uređaj smije reći `UNKNOWN_CHANGE`, a ne dokazani mehanički kvar ili sigurno spoljna buka.

**Gdje:** `psd_live.c::subsegment_instability()`; `asd_interference.c::asd_interference_update()`; `asd_events.c::asd_decide()` spaja provjere kvaliteta, prisustva, HOLD-a i alarma. `audio_quality_state.c` provjerava, između ostalog, clipping, izgubljene uzorke i nevažeće vrijednosti. `ANOMALY_SUSTAINED` je dodatni događaj poslije 12 pouzdanih alarmnih prozora, a ne uslov za prvo paljenje alarma.

**Provjeri sebe:** Da li HOLD znači „sigurno nema kvara”? Ne — znači da odluka iz tog prozora nije pouzdana.


<!-- BEGIN KEY CODE -->
### Ručno isprobaj pravilo alarma

Ilustrativni pragovi: ulaz 100, izlaz 50. Jedan klik predstavlja jedan približno 10-sekundni prozor.

Skor 120 · pouzdan · Skor 80 · pouzdan · Skor 40 · pouzdan · Skor 120 · HOLD · Počni ponovo

Pojednostavljen prikaz vremenskog pravila i HOLD-a. Ne simulira cijeli firmware: greške senzora, odsustvo mašine, commissioning i trajni događaji imaju dodatnu logiku.

### Ključni kod: Histereza i brojanje prekoračenja

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\asd_temporal.c`

**Redovi:** 85–107. Doslovni isječak; okolni kod je izostavljen.

```c

    if (det->active) {
        /* Histereza: iz alarma se izlazi tek ispod NIŽEG praga. Bez toga
         * score koji visi oko praga pali i gasi alarm iz prozora u prozor. */
        if (statistic <= threshold_exit) {
            det->active = 0;
            det->run = 0;
            det->cusum = 0.0f;
        }
    } else {
        /* Strogo veće, isto kao ranije u psd_live.c: score tačno na pragu je
         * normalan. */
        det->run = statistic > threshold_enter ? det->run + 1 : 0;
        int fired = det->run >= det->policy.min_consecutive;
        if (det->policy.cusum_h > 0.0f && det->cusum > det->policy.cusum_h)
            fired = 1;
        if (det->policy.fast_scale > 0.0f &&
            score > threshold_enter * det->policy.fast_scale)
            fired = 1;
        if (fired) det->active = 1;
    }
    return det->active;
}
```

### Ključni kod: Visok skor je već provjeren: nestabilnost aktivira HOLD

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\firmware\esp32s3_asd\main\asd_interference.c`

**Redovi:** 87–102. Doslovni isječak; okolni kod je izostavljen.

```c
    int unreliable =
        (gate->policy.use_tonalness_delta &&
         fabsf(obs->tonalness_delta) > gate->policy.max_abs_tonalness_delta) ||
        obs->subsegment_instability > gate->policy.max_subsegment_instability;
    if (!unreliable) {
        /* The next stable high window starts a fresh temporal run. */
        asd_interference_reset(gate);
        return ASD_INTERFERENCE_PASS;
    }
    gate->hold_active = 1;
    gate->hold_windows++;
    if (gate->hold_windows >= gate->policy.long_hold_windows) {
        gate->warning_emitted = 1;
        return ASD_INTERFERENCE_HOLD_WARNING;
    }
    return ASD_INTERFERENCE_HOLD;
```
<!-- END KEY CODE -->
## 13. Kako smo dokazivali da PC i MCU računaju isto

Postoje tri odvojene provjere. Poređenje je pošteno samo kada oba računaju nad **istim uzorcima**, sa istim parametrima. Dva odvojena snimanja istog ventilatora nijesu isti ulaz.

| Provjera | Kako | Šta dokazuje |
|---|---|---|
| Python ↔ C na PC-u | isti WAV kroz Python referencu i kompajliranu C biblioteku | slaganje algoritamskih implementacija |
| C batch ↔ C streaming | svi uzorci odjednom naspram hopova po 4096 | slaganje dva načina obrade |
| PC ↔ stvarna pločica | pločica šalje snimljeni PCM i svoj feature; PC ponovi račun nad tim PCM-om | slaganje frontend računa na uređaju i PC-u za taj snimak |

**Testovi:** `pc/tests/test_psd_features_c.py`: `test_psd_real_wav_pc_vs_c`, `test_psd_stream_matches_batch`, `test_psd_score_pc_vs_c`. Prvi ima toleranciju 0,002 po feature-u, streaming zahtijeva tačno 0 razlike, a skor relativnu grešku ispod 2e-6. Nemoj miješati dozvoljenu toleranciju i stvarno izmjerenu grešku.

Istorijski zapis u `docs/hardver-verifikacija.md`: najveća PC–C razlika feature-a oko **9,54e-7**, batch–streaming **0**, PC–pločica na živom zvuku **1,698e-6**. To su zabilježena mjerenja, ne novo fizičko mjerenje obavljeno pri pisanju ovog vodiča.

**Pločica:** `psd_verify.c`, režim `ASD_PSD_VERIFY`. **PC:** `pc/tools/psd_verify_compare.py`; provjerava i FNV-1a kontrolni zbir prenesenog PCM-a. Sitne razlike očekujemo zbog float32 i redosljeda računanja.

**Kontrolni zbir** je kratak broj izračunat iz prenesenih podataka; poređenjem otkrivamo greške u prenosu, uz ograničenja takve provjere. **float32** čuva decimalne brojeve sa ograničenom preciznošću, pa račun zaokružuje. Zato npr. `0,123400` i `0,123401` mogu biti prihvatljivo bliski. **Batch** znači obradu već skupljenog snimka, a **streaming** obradu komad po komad dok podaci stižu.

Ovo ne dokazuje da mikrofon savršeno mjeri fizički pritisak, da clipping nije moguć pri bilo kojoj jačini ili da model otkriva svaki kvar. Dokazuje numeričko slaganje provjerenog puta. Ranija log-mel verifikacija nije automatski dokaz za novi PSD frontend — zato je PSD zasebno provjeren.


<!-- BEGIN KEY CODE -->
### Dokaz slaganja: jedan snimak, dva računa

Prođi korake redom. Ključ je da PC i pločica dobiju iste uzorke, ne dva slična snimka.

Sljedeći korak · Vrati na početak

**Zapamti:** Isti ulaz + iste postavke → poređenje izlaza ima smisla.

Šema stvarne metode provjere. Brojevi u zelenoj kutiji su ilustrativni; istorijska izmjerena greška i fajlovi navedeni su u tekstu iznad.

**Tekst koraka animacije:**

- 1. Pločica snimi jedan PCM niz iz mikrofona. Taj niz je zajednički ulaz za poređenje.

- 2. Pločica iz tog PCM-a izračuna svojih 96 obilježja.

- 3. Prenese isti PCM i svoj rezultat na PC. Kontrolni zbir provjerava preneseni niz.

- 4. PC nad tim PCM-om ponovi račun sa istim postavkama.

- 5. Upoređujemo odgovarajuća obilježja i tražimo najveću apsolutnu razliku. Male float razlike nijesu isto što i bit-identičnost.

### Ključni kod: Test istog WAV-a kroz Python i C

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\tests\test_psd_features_c.py`

**Redovi:** 121–135. Doslovni isječak; okolni kod je izostavljen.

```python
def test_psd_real_wav_pc_vs_c(clib):
    clips = fan_clips_or_skip()
    path = clips[0].path
    y, sr = sf.read(path, dtype="float32", always_2d=True)
    assert sr == 16000
    y = np.ascontiguousarray(y[:, 0])
    out = np.zeros(96, np.float32)
    segments = clib.asd_psd_extract(
        y.ctypes.data_as(ctypes.POINTER(ctypes.c_float)), ctypes.c_int(len(y)),
        out.ctypes.data_as(ctypes.POINTER(ctypes.c_float)))
    ref = periodic_features(path)["psd_shape"].astype(np.float32)
    max_diff = float(np.max(np.abs(ref - out)))
    print(f"segments={segments} max|PC-C|={max_diff:.3e}")
    assert segments == 38
    assert max_diff < 2e-3
```
<!-- END KEY CODE -->
## 14. Put do finalnog modela — autoenkoder nije bio jedini pokušaj

Ovo je razvojna istorija, ne spisak svega što je uključeno u finalni firmware. Brojke iz različitih protokola ne treba tumačiti kao savršeno upareno takmičenje.

Za čitanje tabele: **embedding** je opis zvuka koji mreža sama nauči; **kNN** poredi novi opis sa najsličnijim ranijim opisima; **ansambl** kombinuje više modela. **Envelope** prati kako se jačina zvuka mijenja kroz vrijeme. Ostale nazive alternativa zasad posmatraj kao imena pokušaja: za razumijevanje konačnog sistema ne moraš prvo učiti svaki odbačeni metod.

| Faza | Šta smo probali | Šta treba da razumiješ | Gdje |
|---|---|---|---|
| Autoenkoder | baseline i manje AE-tiny mreže | uči da rekonstruiše normalni log-mel; očekivali smo veću grešku za anomaliju, ali razdvajanje nije bilo dovoljno dobro | `pc/asd/model.py`, `train.py`, `quantize.py` |
| Naučeni embedding i klasifikacija | više tipova mašina, režimi/brzine, samonadzirani pokušaj | dobar opis za razlikovanje klasa ne mora sačuvati fine promjene unutar jednog ventilatora | `pc/tools/train_embed.py`, `train_ssl.py` |
| Statistika nad mel opisom | sredine, rasipanja, puna/dijagonalna kovarijansa | pokazalo se da veze među trakama nose informaciju | `pc/tools/bench_research.py` i nastavci 2–6 |
| Promjene statističkog modela | Ledoit–Wolf, PPCA, medijana centra, kNN, robusna kovarijansa, ansambli | neke su pomogle mel modelu, ali nijesu riješile ograničenje opisa zvuka | isti istraživački alati |
| Novi frontend | psd_raw, psd_shape, envelope, kombinacije | visoka frekvencijska rezolucija i oblik spektra donijeli su važan dobitak za ventilator | `bench_periodicity.py` |
| Napredne alternative | order, režimi, logratio, coherence i druge unaprijed navedene varijante | nije svaka fizički zanimljiva ideja dala bolje rezultate | `pc/tools/evaluate_advanced.py` |
| Kasniji kandidati | neprazne trake, audio-hardening, druge regularizacije kovarijanse | dodatna PC istraživanja; ne zamjenjuju fizički provjereni baseline | `results/psd_nonempty`, `audio_hardening`, `psd_covariance` |

Orijentacione istorijske brojke iz `docs/put-do-modela.md`: AE oko 0,451 AUC, embedding oko 0,495, neki mel statistički modeli oko 0,64–0,72, PSD oko 0,864 u tadašnjem protokolu. To nije dokaz da su neuronske mreže generalno loše; govori da ovi konkretni pokušaji nijesu bili najbolji u ovoj postavci. Objašnjenja njihovog neuspjeha tretiraj kao tumačenja potkrijepljena eksperimentima, ne univerzalne zakone.

Za finalno izlaganje koristi noviji pregled u `README.md`: **0,8556 ± 0,0240**, k=10, 20 podjela; odvojena PC referenca **0,8666 ± 0,0270**, k=20, 100 podjela. PSD nije pobijedio za svaku vrstu mašine: fokus ovog uređaja je ventilator. Razvojni benchmark nije nezavisan test cijelog procesa izbora modela.

Ovdje **k=10** znači deset normalnih snimaka za lokalnu kalibraciju. „20 podjela” znači da ponovimo ocjenu sa različitim izborima kalibracionih snimaka. Broj prije `±` je prosječni AUC, a broj poslije pokazuje koliko je varirao između podjela. **Benchmark** je takvo dogovoreno poređenje na skupu podataka, a ne proba svakog mogućeg stvarnog kvara.

**Zašto finalni izbor:** koristan spektralni opis za ventilator, bolji razvojni rezultat među ispitivanim pristupima, mali model i izvodljiv račun na ESP32. Konačan metod je **Welch + 96 log-spektralnih obilježja + standardizacija + lokalni centar + Ledoit–Wolf Mahalanobisov skor + provjere i vremenska odluka**.

## 15. Keras, TFLite i TFLM — gdje su bili

**Keras** je alat kojim smo u Pythonu sastavili mrežu od slojeva i učili njene parametre. Poslije učenja model smo pretvarali u **TensorFlow Lite** format, fajl `.tflite`. **TFLite Micro / TFLM** je softver na mikrokontroleru koji izvršava podržane operacije takvog modela. Učenje mijenja parametre pomoću primjera; **inferenca** samo koristi već naučene parametre da obradi novi ulaz.

**int8 kvantizacija** približno predstavlja decimalne vrijednosti pomoću 256 cjelobrojnih nivoa. Skala i pomak govore koju decimalnu vrijednost pojedini nivo predstavlja. Kao grublji lenjir: troši manje memorije, ali uvodi zaokruživanje, pa provjeravamo da li rezultat ostaje dovoljno dobar.

Put istorijskog AE-a: `pc/asd/model.py::build_ae()` → `pc/asd/train.py` → `.keras` → `pc/asd/quantize.py::convert()` → `.tflite` → `pc/tools/gen_model_header.py` → `firmware/esp32s3_asd/main/tflm_infer.cc`.

Finalni PSD tok ne izvršava AE niti TFLM inferencu. U `app_main.c` grana `ASD_PSD_LIVE` dolazi prije `tflm_init()`. To što su stari fajlovi ostali u repozitorijumu ne znači da su finalni model.

**Autoenkoder najprostije:** stisne opis zvuka u manji kod pa pokuša vratiti original. Razlika original–rekonstrukcija je skor. Problem je što može dobro rekonstruisati i anomaliju, ili loše rekonstruisati normalan zvuk novog domena.


<!-- BEGIN KEY CODE -->
### Autoenkoder: original → uski kod → rekonstrukcija

Uporedi ulaz i rekonstrukciju. Isprobaj anomaliju koju mreža takođe dobro kopira: mala greška tada nije dokaz normalnog rada.

Primjer · Normalan zvuk, dobra kopija · Anomalija, loša kopija · Anomalija, dobra kopija

**Zapamti:** Autoenkoderov skor mjeri grešku kopiranja. To nije direktna mjera zdravlja mašine.

Izmišljeni vektori od četiri broja, bez izvršavanja neuronske mreže. Služe samo da pokažu ideju i mogući promašaj.

### Ključni kod: Istorijski Keras autoenkoder

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\asd\model.py`

**Redovi:** 19–37. Doslovni isječak; okolni kod je izostavljen.

```python
        x = layers.Dense(width, name=f"enc_{i}")(x)
        x = layers.BatchNormalization(name=f"enc_bn_{i}")(x)
        x = layers.ReLU(name=f"enc_relu_{i}")(x)
    x = layers.Dense(bottleneck, name="bottleneck")(x)
    x = layers.BatchNormalization(name="bn_bottleneck")(x)
    x = layers.ReLU(name="relu_bottleneck")(x)
    for i in range(depth):
        x = layers.Dense(width, name=f"dec_{i}")(x)
        x = layers.BatchNormalization(name=f"dec_bn_{i}")(x)
        x = layers.ReLU(name=f"dec_relu_{i}")(x)
    out = layers.Dense(input_dim, name="output")(x)
    m = tf.keras.Model(inp, out, name=f"ae_w{width}d{depth}b{bottleneck}")
    m.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    return m


# Pareto sweep konfiguracije (E2). input_dim=640 osim *mel64 varijanti.
SWEEP = {
    "baseline":  dict(width=128, depth=4, bottleneck=8),
```

### Ključni kod: Keras → TFLite, opciono int8 — istorijski tok

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\asd\quantize.py`

**Redovi:** 22–36. Doslovni isječak; okolni kod je izostavljen.

```python
def convert(keras_path: Path, rep_data: np.ndarray | None) -> bytes:
    import tensorflow as tf
    m = tf.keras.models.load_model(keras_path)
    conv = tf.lite.TFLiteConverter.from_keras_model(m)
    if rep_data is not None:
        conv.optimizations = [tf.lite.Optimize.DEFAULT]

        def rep():
            for i in range(0, len(rep_data), 1):
                yield [rep_data[i:i + 1].astype(np.float32)]
        conv.representative_dataset = rep
        conv.target_spec.supported_ops = [tf.lite.OpsSet.TFLITE_BUILTINS_INT8]
        conv.inference_input_type = tf.int8
        conv.inference_output_type = tf.int8
    return conv.convert()
```
<!-- END KEY CODE -->
## 16. „ric”: vjerovatno ROC, ali naziv treba potvrditi

Iz napisanog ne mogu sigurno znati šta znači „ric”. Ako misliš na **ROC**, to je kriva koja pokazuje odnos otkrivenih anomalija i lažnih alarma dok mijenjamo prag.

**TPR:** koliko stvarnih anomalija smo uhvatili. **FPR:** koliko normalnih slučajeva smo pogrešno označili. **AUC:** površina ispod ROC krive, mjera rangiranja preko različitih pragova. Oko 0,5 znači slučajno rangiranje; 1 znači savršeno razdvajanje na tom skupu. AUC 0,856 nije „85,6% tačnih odluka” niti garantuje koristan alarm pri izabranom pragu. **pAUC** posmatra dio ROC krive, npr. područje malog FPR-a, prema korišćenom protokolu.

Primjer: od 10 anomalnih snimaka označimo 8 → TPR je 80%. Od 100 normalnih pogrešno označimo 5 → FPR je 5%. To je jedna tačka na ROC krivoj za jedan prag. Mijenjanjem praga dobijamo druge tačke. AUC sažima koliko dobro skorovi **poređaju anomalije iznad normalnih snimaka**, prije nego što odaberemo jedan prag za rad uređaja.

**Gdje:** `pc/asd/eval.py::dcase_metrics()` i `roc_auc_score` u benchmark alatima. Ako je „ric” bio **ring buffer**, objašnjen je u odjeljku 2; za neku treću oznaku treba vidjeti originalnu riječ.


<!-- BEGIN KEY CODE -->
### Prag: više detekcija ili manje lažnih alarma?

Svaka tačka je jedan snimak. Plavo označava stvarno normalne snimke, narandžasto stvarne anomalije. Sve desno od praga označavamo kao anomaliju.

Prag skora

**Zapamti:** Niži prag hvata više anomalija, ali može označiti i više normalnih snimaka.

Mali izmišljeni skup za objašnjenje TPR/FPR. Ovo je odluka po jednom skoru, bez pravila tri prozora; nije stvarni ROC rezultat projekta.

### Ključni kod: Računanje ROC AUC i pAUC

**Puna putanja:** `C:\Users\mihaj\Desktop\master new\pc\asd\eval.py`

**Redovi:** 47–56. Doslovni isječak; okolni kod je izostavljen.

```python
def dcase_metrics(scores: np.ndarray, labels: np.ndarray, domains: np.ndarray) -> dict:
    """AUC_source, AUC_target (normal iz domena + SVE anomalije), pAUC, harmonijska sredina."""
    res = {}
    for dom in ("source", "target"):
        mask = ((domains == dom) & (labels == 0)) | (labels == 1)
        res[f"auc_{dom}"] = roc_auc_score(labels[mask], scores[mask])
    res["pauc"] = roc_auc_score(labels, scores, max_fpr=P_AUC_FPR)
    vals = [res["auc_source"], res["auc_target"], res["pauc"]]
    res["hmean"] = stats.hmean(vals)
    return res
```
<!-- END KEY CODE -->
## 17. Šta zaista smiješ pokazati kao rezultat

Numeričko slaganje, vrijeme računanja, benchmark i fizička detekcija su četiri različita dokaza.

| Tvrdnja | Stvarni obim |
|---|---|
| Izvodljivo na ESP32-S3 | oko 716–728 ms računanja obilježja i skora za približno 10 s zvuka; nije ukupno kašnjenje alarma |
| Fizička proba sa tonom 1 kHz | alarm i ANOMALY_SUSTAINED; potvrđena detekcija te stabilne akustičke promjene |
| Proba sa papirićem GUIDED25 | FAIL: 1/3 blokova detektovan; alarm prenesen u dio oporavka |
| Govor i vrata u toj probi | bez alarma u malom posmatranom uzorku; ne dokazuje opštu otpornost na buku |
| valid_physical_result | zapis je upotrebljiv za tumačenje; ne znači da je eksperiment prošao |

Izvor: `docs/rezultat-finalna-validacija-2026-08-27.md`. Jedan ventilator i vještačke pobude ne dokazuju dijagnozu stvarnog mehaničkog kvara. `dropped=0` samo kaže da brojač nije prijavio izgubljene uzorke; bez validnog audio toka to nije dovoljan dokaz dobrog snimanja.

**Za profesora:** „Potvrdio sam da algoritam može samostalno raditi na mikrokontroleru i detektovati stabilnu promjenu zvuka u testiranoj postavci. Nestabilne pobude i razdvajanje uzroka promjene ostaju ograničenja, što se vidi i iz neuspjeha dijela testa sa papirićem.”

## 18. Redosljed pokazivanja koda profesoru

1. `app_main.c`: ulaz u finalni PSD režim.
2. `audio_i2s.h`, `pins.h`, `audio_i2s.c::audio_i2s_init()`: 16 kHz, žice, format i prijem.
3. `psd_features_c.h`: 8192 / 4096 / 96.
4. `psd_features_c.c`: Hann → FFT → snaga → Welch → trake → centriranje.
5. `pc/tools/gen_psd_model_header.py`: učenje normalne kovarijanse i izvoz; samo pokaži da `psd_model_data.h` sadrži rezultat.
6. `psd_features_c.c::asd_psd_score()`: nekoliko petlji koje računaju Mahalanobisov skor.
7. `psd_live.c`: CAL → DERIVE → VERIFY → DET.
8. `asd_temporal.c`, `asd_interference.c`, `asd_events.c`: tri prekoračenja, HOLD i konačna odluka.
9. `pc/tests/test_psd_features_c.py`, `psd_verify_compare.py`: dokazi numeričkog slaganja.
10. Dokument završnih proba: stvarni rezultat i ograničenja.

Za kratko izlaganje dovoljno je ovih deset stanica. Ne treba pokazivati svaki pomoćni fajl. HTML verzija ispod objašnjenja prikazuje odabrane stvarne isječke sa putanjom i brojem reda.

## 19. Samoprovjera prije razgovora

Pokušaj bez gledanja: objasni razliku I2S–PCM; izračunaj 8000 Hz, 0,512 s i 1,953 Hz; nacrtaj `[A B]`, `[B C]`; razlikuj STFT od Welch prosjeka; objasni zašto mel nije finalni frontend; opiši kovarijansu bez formule; reci šta uči PC, a šta pločica; objasni zašto HOLD nije dokaz buke; navedi tri nivoa numeričke provjere; reci zašto AUC nije procenat tačnih alarma.

Ako zapneš, vrati se samo na taj odjeljak. Cilj nije da naučiš rečenice napamet, nego da možeš odgovoriti: **šta ulazi, šta izlazi, zašto nam taj korak treba i gdje je urađen**.

## 20. Izvori za dalje čitanje

Projektni izvori imaju prednost za tvrdnju šta smo stvarno uradili: `README.md`, `docs/put-do-modela.md`, `docs/odluka-finalni-model.md`, `docs/hardver-verifikacija.md`, `docs/rezultat-finalna-validacija-2026-08-27.md`, te navedeni kod. Starije tekstove koristi za istoriju; njihovi pragovi i zaključci ne zamjenjuju noviju završnu reviziju.

Za definiciju Welch postupka, preklapanje i razliku `density`/`spectrum`: [SciPy dokumentacija](https://docs.scipy.org/doc/scipy/reference/generated/scipy.signal.welch.html). Za regularizaciju kovarijanse: [scikit-learn LedoitWolf](https://scikit-learn.org/stable/modules/generated/sklearn.covariance.LedoitWolf.html). To su dopunski izvori teorije, ne dokazi naših fizičkih mjerenja.
