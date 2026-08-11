/* Bring-up mod za INA226 (E5): I2C scan + provjera identiteta + očitanja.
 * Prvi boot armira test; sljedeći boot mjeri i čuva rezultat u NVS-u; naredni
 * boot ispisuje sačuvani rezultat bez prepisivanja.
 *
 * Ulazak u mod: build sa -DASD_INA_TEST (set ASD_INA_TEST=1, pa
 * idf.py reconfigure build flash). Ne dira audio ni model.
 */
#ifndef ASD_INA226_TEST_H
#define ASD_INA226_TEST_H

#ifdef __cplusplus
extern "C" {
#endif

void ina226_test_run(void);

#ifdef __cplusplus
}
#endif
#endif
