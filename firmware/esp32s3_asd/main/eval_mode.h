/* E4 eval mod: čita 16 kHz/16-bit mono WAV klipove sa FAT particije ("storage",
 * fatfsgen slika, read-only mount) i za svaki ispiše CSV red na UART:
 *   fajl,score,feat_ms,inf_ms
 * Score-ovi se porede sa PC referencom (pc/tools/prepare_eval_clips.py) —
 * identičan ulaz => identičan izlaz (streaming featuri su bit-jednaki batch putu).
 *
 * Ulazak u mod: taster (PIN_BUTTON na GND) držan pri bootu, ili -DASD_EVAL_MODE.
 */
#ifndef ASD_EVAL_MODE_H
#define ASD_EVAL_MODE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Vraća se tek kad obradi sve klipove; 0 = OK. */
int eval_mode_run(void);

#ifdef __cplusplus
}
#endif
#endif
