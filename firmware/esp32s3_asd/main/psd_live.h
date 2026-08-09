/* Samostalni PSD detektor: čekanje -> lokalna kalibracija na novom ventilatoru
 * -> neprekidna detekcija, sve na pločici i bez računara.
 *
 * Model (matrica 96x96 + normalizacija) je naučen unaprijed iz 990 ispravnih
 * DCASE ventilatora i stoji u flešu; ovdje se mjeri SAMO centar novog primjerka.
 * Vidi docs/odluka-finalni-model.md i docs/istrazivanje-psd-model.md.
 *
 * Build:  set ASD_PSD_LIVE=1  &&  idf.py reconfigure build flash monitor
 */
#ifndef ASD_PSD_LIVE_H
#define ASD_PSD_LIVE_H

void psd_live_run(void);

#endif
