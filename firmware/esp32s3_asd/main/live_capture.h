/* Živi klip + score + snimak: uređaj snimi jedan klip sa mikrofona, izračuna
 * score SVOJIM lancem (isti streaming kod kao živi rad), pa isti taj snimak
 * pošalje na PC. PC ga onda boduje svojim pipeline-om i poredi.
 *
 * Zašto: dosadašnje PC↔uređaj poređenje (1.5e-04) radjeno je nad klipovima iz
 * dataseta koji su na uređaj stigli preko flash particije — dakle nad
 * identičnim bajtovima. Ovim se ista provjera radi nad ŽIVIM zvukom iz
 * mikrofona, gdje ulaz nastaje na samom uređaju.
 *
 * Ulazak u mod: build sa -DASD_LIVE_CAPTURE (set ASD_LIVE_CAPTURE=1, pa
 * idf.py reconfigure build flash). PC strana: pc/tools/live_compare.py
 */
#ifndef ASD_LIVE_CAPTURE_H
#define ASD_LIVE_CAPTURE_H

#ifdef __cplusplus
extern "C" {
#endif

/* Očekuje da su asd_features_init(), tflm_init(), audio_i2s_init() i
 * audio_i2s_start() već pozvani. */
void live_capture_run(void);

#ifdef __cplusplus
}
#endif
#endif
