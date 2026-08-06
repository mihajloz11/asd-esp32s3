/* Prilagođavanje praga stvarnom okruženju, na samom uređaju (E6 primijenjen na
 * živi zvuk).
 *
 * Problem koji rješava: prag iz firmware-a (ASD_SCORE_THRESHOLD) izračunat je
 * nad trening podacima mašine iz DCASE dataseta. U bilo kom stvarnom prostoru
 * score je reda desetica, pa taj prag proglašava sve anomalijom i sistem je
 * beskoristan — klasičan domain shift.
 *
 * Postupak: uređaj K puta boduje kratke prozore živog zvuka, tretira ih kao
 * NORMALNO stanje, momentnom metodom fituje gamma raspodjelu (calib_gamma.c)
 * i uzima p-ti percentil kao novi prag. Zatim prelazi u detekciju sa tim
 * pragom. Nema backpropa, nema treninga — samo Welford i inverzna gamma CDF.
 *
 * Ulazak u mod: build sa -DASD_LIVE_ADAPT (set ASD_LIVE_ADAPT=1, pa
 * idf.py reconfigure build flash).
 */
#ifndef ASD_LIVE_ADAPT_H
#define ASD_LIVE_ADAPT_H

#ifdef __cplusplus
extern "C" {
#endif

/* Očekuje inicijalizovane featuring, TFLM i audio. Ne vraća se. */
void live_adapt_run(void);

#ifdef __cplusplus
}
#endif
#endif
