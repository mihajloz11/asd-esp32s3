/* LEGACY MOD (ASD_LIVE_ADAPT) — prethodi Fazi 1 i NIJE finalni tok.
 * Sadrzi "warn and continue" koji je u finalnom putu (psd_live.c) zabranjen.
 * Cuva se jer su na njemu radjena mjerenja od 08.08.2026; ne uzimati za uzor
 * i ne uvoziti u novi kod.
 * Vidi live_adapt.h. */
#include "live_adapt.h"

#include <math.h>
#include <stdio.h>

#include "freertos/FreeRTOS.h"
#include "freertos/task.h"
#include "driver/gpio.h"
#include "esp_log.h"

#include "pins.h"
#include "audio_i2s.h"
#include "features_c.h"
#include "tflm_infer.h"
#include "calib_gamma.h"
#include "model_data.h"

static const char *TAG = "adapt";

/* Prozor od 2 s umjesto 10 s: kalibracija traži dovoljno uzoraka za procjenu
 * raspodjele, a 30 x 10 s = 5 minuta je predugo za demo. 2 s daje ~59 vektora
 * po prozoru — score je nešto šumniji, ali raspodjela se fituje 5x brže. */
#define WIN_SEC        2
#define HOPS_PER_WIN   (AUDIO_SR * WIN_SEC / ASD_HOP)
#define N_CALIB        30                  /* 30 x 2 s = 60 s kalibracije */
/* DVOSTRANI prag. Mjereno 08.08: u tihoj sobi model treniran na zvuku mašine
 * daje score ~71; kad se pusti glasan zvuk, score PADNE na ~48, ne poraste.
 * Greška rekonstrukcije je udaljenost od naučene raspodjele, a ne mjera jačine
 * zvuka — tišina je modelu "dalja" od nekih glasnih zvukova. Jednostrani prag
 * (samo score > gornji) zato propušta pola stvarnih promjena u okruženju. */
#define CALIB_P_HI     0.99f               /* gornja granica normalnog rada */
#define CALIB_P_LO     0.01f               /* donja granica */

static asd_stream_t stream;

static float score_window(void) {
    static int16_t pcm[ASD_HOP];
    static float hop[ASD_HOP];
    static float vec[ASD_INPUT_DIM];

    asd_stream_reset(&stream);
    float sum = 0.0f;
    int n = 0;

    for (int h = 0; h < HOPS_PER_WIN; h++) {
        audio_read(pcm, ASD_HOP);
        for (int i = 0; i < ASD_HOP; i++)
            hop[i] = (float)pcm[i] / 32768.0f;

        if (asd_stream_push_hop(&stream, hop) &&
            asd_stream_vector(&stream, asd_norm_mean, asd_norm_std, vec)) {
            sum += tflm_score_vector(vec);
            n++;
        }
    }
    return n ? sum / (float)n : 0.0f;
}

/* Čekanje da se okruženje umiri prije kalibracije.
 *
 * Zašto postoji: kalibracija je do sada kretala odmah po bootu, a boot se
 * dešava tačno kad se ploča fleširala ili se pokrenuo alat na računaru — pa je
 * ventilator laptopa bio zavrtio i kalibracija je učila NJEGA kao normalno
 * stanje. Izmjereno: score se popne sa 30 na 77 za 18 s, stoji dok ventilator
 * radi, pa padne na 12 kad se umiri. Prag izračunat na 77 poslije toga ne
 * može da opali ni na šta.
 *
 * Dva uslova, oba moraju biti ispunjena:
 *   1) prođe MIN_WARM prozora — pokriva silazak ventilatora (mjereno ~2 min)
 *   2) zadnjih STAB_WIN prozora se razlikuju manje od STAB_TOL relativno —
 *      brani od kalibracije usred prelaza
 */
#define MIN_WARM   60        /* 60 x 2 s = 120 s */
#define STAB_WIN   5
#define STAB_TOL   0.15f
#define MAX_WARM   150       /* gornja granica cekanja: 5 min */

static int wait_until_settled(void) {
    float ring[STAB_WIN];
    int n = 0;

    for (int i = 0; i < MAX_WARM; i++) {
        float s = score_window();
        ring[n % STAB_WIN] = s;
        n++;

        float spread = -1.0f;
        int stable = 0;
        if (n >= STAB_WIN) {
            float mn = ring[0], mx = ring[0], sum = 0.0f;
            for (int j = 0; j < STAB_WIN; j++) {
                if (ring[j] < mn) mn = ring[j];
                if (ring[j] > mx) mx = ring[j];
                sum += ring[j];
            }
            float mean = sum / STAB_WIN;
            spread = mean > 0.0f ? (mx - mn) / mean : 1.0f;
            stable = spread < STAB_TOL;
        }

        printf("WAIT %d/%d score=%.2f spread=%.3f %s\n",
               i + 1, MIN_WARM, s, spread,
               (i + 1 >= MIN_WARM && stable) ? "umireno" : "ceka");

        if (i + 1 >= MIN_WARM && stable) return 1;
    }
    return 0;
}

void live_adapt_run(void) {
    gamma_calib_t cal;
    gamma_calib_reset(&cal);

    ESP_LOGI(TAG, "cekam da se okruzenje umiri (min %d s) prije kalibracije...",
             MIN_WARM * WIN_SEC);
    if (!wait_until_settled())
        ESP_LOGW(TAG, "okruzenje se nije umirilo u %d s — kalibrisem svejedno",
                 MAX_WARM * WIN_SEC);

    ESP_LOGI(TAG, "=== PRILAGODJAVANJE PRAGA ZIVOM OKRUZENJU ===");
    ESP_LOGI(TAG, "fabricki prag (iz DCASE trening podataka): %.5f",
             (float)ASD_SCORE_THRESHOLD);
    ESP_LOGI(TAG, "kalibracija: %d prozora po %d s = %d s. NE PRAVI BUKU.",
             N_CALIB, WIN_SEC, N_CALIB * WIN_SEC);

    float smin = 1e30f, smax = -1e30f;
    for (int i = 0; i < N_CALIB; i++) {
        float s = score_window();
        gamma_calib_add(&cal, s);
        if (s < smin) smin = s;
        if (s > smax) smax = s;
        printf("CAL %2d/%d  score=%.5f\n", i + 1, N_CALIB, s);
    }

    double var = cal.m2 / (cal.n - 1);
    double sd = sqrt(var);
    /* Momentna procjena gamma parametara (isto što calib_gamma radi interno) */
    double k = (cal.mean * cal.mean) / var;
    double theta = var / cal.mean;

    float thr = gamma_calib_threshold(&cal, CALIB_P_HI);
    float thr_lo = gamma_calib_threshold(&cal, CALIB_P_LO);

    ESP_LOGI(TAG, "--- kalibracija gotova ---");
    ESP_LOGI(TAG, "n=%d  mean=%.5f  sd=%.5f  min=%.5f  max=%.5f",
             cal.n, cal.mean, sd, smin, smax);
    ESP_LOGI(TAG, "gamma fit: k=%.4f theta=%.5f", k, theta);
    ESP_LOGI(TAG, "NORMALAN OPSEG: %.5f .. %.5f   [fabricki prag je bio %.5f]",
             thr_lo, thr, (float)ASD_SCORE_THRESHOLD);
    printf("ADAPTTHR n=%d mean=%.6f sd=%.6f k=%.6f theta=%.6f p=%.4f thr=%.6f lo=%.6f factory=%.6f\n",
           cal.n, cal.mean, sd, k, theta, CALIB_P_HI, thr, thr_lo,
           (float)ASD_SCORE_THRESHOLD);

    if (thr <= 0.0f) {
        ESP_LOGE(TAG, "kalibracija nije uspjela (premala varijansa?)");
        return;
    }

    ESP_LOGI(TAG, "--- detekcija radi neprekidno: lupi, zvizni, pusti muziku ---");
    ESP_LOGI(TAG, "LED (GPIO%d) svijetli = normalno, gasi se = anomalija", PIN_LED);

    /* Beskonačna petlja: uređaj je od ovog trenutka detektor. Svaki prozor daje
     * jednu DET liniju koju pc/tools/live_monitor.py crta u realnom vremenu. */
    int i = 0, n_anom = 0;
    while (1) {
        float s = score_window();
        int hi = s > thr, lo = s < thr_lo;
        int anom = hi || lo;
        n_anom += anom;
        i++;

        /* LED: svijetli dok je normalno, gasi se na anomaliju. Ako LED nije
         * fizički spojen, poziv je bezopasan — pin samo mijenja nivo. */
        gpio_set_level(PIN_LED, !anom);

        printf("DET %d score=%.5f lo=%.5f hi=%.5f led=%d anom=%d total_anom=%d %s\n",
               i, s, thr_lo, thr, !anom, anom, n_anom,
               anom ? (hi ? "ANOMALIJA(iznad)" : "ANOMALIJA(ispod)") : "normal");
    }
}
