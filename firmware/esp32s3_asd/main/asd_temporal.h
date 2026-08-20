/* Faza 4 — vremenska odluka na nivou odstupanja.
 *
 * Host-testabilno, bez ESP-IDF zavisnosti, isti obrazac kao
 * `audio_quality_state.c`, `asd_events.c` i `asd_operator.c`.
 *
 * ZAŠTO POSTOJI. Do sada je alarm palio poslije 3 uzastopna prozora iznad
 * praga. To je bila razumna pretpostavka, ali nikad izmjerena. Faza 4 ju je
 * izmjerila na normalnim podacima
 * ([`derive_temporal_policy.py`](../../../pc/tools/derive_temporal_policy.py) →
 * [`asd_temporal_policy_v1.json`](../../../pc/config/asd_temporal_policy_v1.json))
 * i rezultat je bio djelimično suprotan očekivanju:
 *
 *   - **EWMA i CUSUM su GORI**, ne bolji. Oba PRENOSE kratku pobudu kroz više
 *     prozora, pa jedan glasan udarac drži statistiku iznad praga dovoljno
 *     dugo da dopuni niz od tri. Izmjereno: 3 uzastopna prozora daju 0 lažnih
 *     alarma na sat i reakciju 0,004 na pobudu od jednog prozora, dok
 *     EWMA(0,4) daje 5,40 lažnih na sat i reakciju 0,59. CUSUM je najgori,
 *     0,72. Oba su odbačena mjerenjem, ne mišljenjem.
 *   - **Histereza pomaže**, i to tamo gdje je najvažnije. Uz isti broj lažnih
 *     alarma (0) i isto kašnjenje (3 prozora), izlazni prag na 0,7 ulaznog
 *     prepolovljuje alarmne epizode kad se akustika pomjeri: 11,16 → 5,40
 *     epizoda na sat na klipovima DRUGOG fizičkog ventilatora.
 *   - **Prag je slabija karika od pravila.** U 10 od 40 kalibracija pomjeraj
 *     od 3 sd nikad ne dosegne prag `sredina + 3 sd LOO`, bez obzira na
 *     vremensko pravilo. To je nalaz o pragu i ostaje otvoren.
 *
 * ŠTA OVO NE RADI. Ne odlučuje o prisustvu mašine i ne tvrdi uzrok. Zove ga
 * `asd_events.c` na nivou `DEVIATION`, tek pošto viši nivoi hijerarhije prođu.
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

/* Pauzira uspon ka alarmu, ali ZADRŽAVA alarm koji već traje.
 *
 * Zove se kad viši nivo hijerarhije privremeno preuzme odluku — konkretno kad
 * nivo padne ispod gate-a prisustva, pa se odstupanje ne ocjenjuje. Alarm se
 * ne smije obrisati samo zato što je mašina na trenutak utihnula: ništa ga
 * nije poništilo, a tiho gašenje bi značilo da uređaj zaboravi odstupanje koje
 * je stvarno izmjerio. */
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
