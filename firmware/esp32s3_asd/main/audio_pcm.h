/* Pretvaranje INMP441 uzorka (24-bit MSB u 32-bit slotu) u int16.
 * Bez ESP-IDF zavisnosti, da ga host testovi zovu direktno. */
#ifndef AUDIO_PCM_H
#define AUDIO_PCM_H

#include <stdint.h>

/* >>14 daje pun 16-bit opseg za normalan nivo. Vrijednosti van opsega se
 * zasicuju umjesto da se prevrnu u suprotan znak, pa ih kapija klipovanja
 * vidi. Za |raw >> 14| <= 32767 rezultat je isti kao ranije. */
static inline int16_t audio_pcm_from_raw(int32_t raw) {
    int32_t v = raw >> 14;
    if (v > INT16_MAX) return INT16_MAX;
    if (v < INT16_MIN) return INT16_MIN;
    return (int16_t)v;
}

/* |raw| bez prekoracenja i za INT32_MIN, ograniceno na INT32_MAX. */
static inline int32_t audio_pcm_raw_magnitude(int32_t raw) {
    int64_t a = raw < 0 ? -(int64_t)raw : (int64_t)raw;
    return a > INT32_MAX ? INT32_MAX : (int32_t)a;
}

#endif
