/* Faza 4: vremenska odluka na nivou odstupanja. Bez ESP-IDF zavisnosti.
 *
 * Pravilo je izvedeno iz normalnih podataka (derive_temporal_policy.py ->
 * asd_temporal_policy_v1.json): tri uzastopna prozora iznad ulaza, izlaz uz
 * histerezu. EWMA i CUSUM su izmjereni i odbaceni, jer prenose kratku pobudu
 * kroz vise prozora (5,40 laznih alarma na sat naspram 0). Histereza je
 * prepolovila epizode na drugom ventilatoru (11,16 -> 5,40 na sat).
 * U firmveru su ulaz i izlaz apsolutni pragovi iz commissioninga.
 *
 * Ne odlucuje o prisustvu i ne tvrdi uzrok; zove ga asd_events.c na nivou
 * DEVIATION.
 */
#ifndef ASD_TEMPORAL_H
#define ASD_TEMPORAL_H

#ifdef __cplusplus
extern "C" {
#endif

#define ASD_TEMPORAL_POLICY "asd-temporal-policy-v2.0.0-development"
#define ASD_TEMPORAL_POLICY_ID 0x54505632u

typedef struct {
    int min_consecutive;   /* uzastopnih prozora iznad ulaznog praga */
    float ewma_alpha;      /* 0 = isključen (izmjereno gorim, vidi zaglavlje) */
    float enter_scale;     /* legacy provenance only; update() ga ne koristi */
    float exit_scale;      /* legacy provenance only; update() ga ne koristi */
    float cusum_k;         /* 0 = isključen */
    float cusum_h;
    float fast_scale;      /* 0 = isključen; jedan ekstreman prozor pali odmah */
} asd_temporal_policy_t;

typedef struct {
    float ewma;
    int ewma_valid;
    int run;               /* uzastopnih prozora iznad ulaznog praga */
    float cusum;
    int active;            /* 1 = u alarmu */
    asd_temporal_policy_t policy;
} asd_temporal_t;

asd_temporal_policy_t asd_temporal_default_policy(void);
void asd_temporal_init(asd_temporal_t *det, const asd_temporal_policy_t *policy);

/* Briše cijelu tekuću dinamiku, uključujući i sam alarm. Za slučaj kad
 * odstupanje više nema smisla mjeriti: kvar senzora, nova sesija, nova
 * kalibracija. */
void asd_temporal_reset(asd_temporal_t *det);

/* Pauzira uspon ka alarmu, ali ZADRZAVA alarm koji traje. Zove se kad visi
 * nivo hijerarhije preuzme odluku, npr. kad nivo padne ispod gate-a
 * prisustva. */
void asd_temporal_suspend(asd_temporal_t *det);

/* Jedan prozor ulazi, stanje alarma izlazi (1 = u alarmu).
 *
 * Mora dati IDENTIČAN niz kao `run_rule()` u `derive_temporal_policy.py` na
 * istim ulazima; `pc/tests/test_asd_temporal_c.py` to i provjerava. */
int asd_temporal_update(asd_temporal_t *det, float score,
                        float threshold_enter, float threshold_exit);

#ifdef __cplusplus
}
#endif

#endif
