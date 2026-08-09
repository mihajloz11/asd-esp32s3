/* PC<->uređaj provjera PSD front-enda na ŽIVOM mikrofonu.
 *
 * Zašto postoji: laboratorijski test (pc/tests/test_psd_features_c.py) dokazuje
 * da se C i Python slažu na DCASE WAV-u, ali ne i da lanac I2S -> shift -> PCM
 * daje uređaju iste uzorke koje PC vidi. Ovaj mod snimi 10 s živog zvuka,
 * izračuna feature TAČNO kao živi rad (streaming) i pošalje i feature i sam
 * snimak, pa PC ponovi račun nad istim uzorcima.
 *
 * Build:  set ASD_PSD_VERIFY=1  &&  idf.py reconfigure build flash
 * PC:     ../.venv/Scripts/python.exe tools/psd_verify_compare.py --port COM4
 */
#ifndef ASD_PSD_VERIFY_H
#define ASD_PSD_VERIFY_H

void psd_verify_run(void);

#endif
