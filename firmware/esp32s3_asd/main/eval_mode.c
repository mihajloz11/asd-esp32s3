#include "eval_mode.h"
#include "features_c.h"
#include "tflm_infer.h"
#include "model_data.h"
#include "calib_gamma.h"

#include <stdio.h>
#include <string.h>
#include <dirent.h>

#include "esp_vfs_fat.h"
#include "esp_timer.h"
#include "esp_log.h"

static const char *TAG = "eval";
#define MOUNT_POINT "/clips"

/* Minimalni RIFF parser: nađe 'fmt ' i 'data' chunk. Vraća broj uzoraka i
 * pozicionira fajl na početak podataka; 0 = greška. Očekuje PCM16 mono 16 kHz. */
static long wav_open(FILE *f) {
    uint8_t hdr[12];
    if (fread(hdr, 1, 12, f) != 12 || memcmp(hdr, "RIFF", 4) || memcmp(hdr + 8, "WAVE", 4)) {
        ESP_LOGE(TAG, "nije RIFF/WAVE");
        return 0;
    }
    uint16_t fmt = 0, ch = 0, bits = 0;
    uint32_t sr = 0;
    for (;;) {
        uint8_t chdr[8];
        if (fread(chdr, 1, 8, f) != 8) return 0;
        uint32_t sz = chdr[4] | (chdr[5] << 8) | (chdr[6] << 16) | ((uint32_t)chdr[7] << 24);
        if (!memcmp(chdr, "fmt ", 4)) {
            uint8_t b[16];
            if (sz < 16 || fread(b, 1, 16, f) != 16) return 0;
            fmt = b[0] | (b[1] << 8);
            ch = b[2] | (b[3] << 8);
            sr = b[4] | (b[5] << 8) | (b[6] << 16) | ((uint32_t)b[7] << 24);
            bits = b[14] | (b[15] << 8);
            if (sz > 16) fseek(f, sz - 16, SEEK_CUR);
        } else if (!memcmp(chdr, "data", 4)) {
            if (fmt != 1 || ch != 1 || sr != 16000 || bits != 16) {
                ESP_LOGE(TAG, "format nije PCM16 mono 16k (fmt=%u ch=%u sr=%lu bits=%u)",
                         fmt, ch, (unsigned long)sr, bits);
                return 0;
            }
            return (long)(sz / 2);
        } else {
            fseek(f, (sz + 1) & ~1u, SEEK_CUR); /* chunkovi su parno poravnati */
        }
    }
}

static int score_file(const char *path, float *out_score) {
    FILE *f = fopen(path, "rb");
    if (!f) { ESP_LOGE(TAG, "fopen %s", path); return -1; }
    long n_samples = wav_open(f);
    if (n_samples <= 0) { fclose(f); return -1; }

    static asd_stream_t stream;
    static int16_t pcm[ASD_HOP];
    static float hop_f32[ASD_HOP];
    static float vec[ASD_INPUT_DIM];
    asd_stream_reset(&stream);

    int64_t t_feat = 0, t_inf = 0;
    double score_sum = 0.0;
    int n_vec = 0;
    long left = n_samples;
    while (left >= ASD_HOP) {
        if (fread(pcm, sizeof(int16_t), ASD_HOP, f) != ASD_HOP) break;
        left -= ASD_HOP;
        for (int i = 0; i < ASD_HOP; i++)
            hop_f32[i] = (float)pcm[i] / 32768.0f;
        int64_t a = esp_timer_get_time();
        int nf = asd_stream_push_hop(&stream, hop_f32);
        int64_t b = esp_timer_get_time();
        t_feat += b - a;
        if (nf && asd_stream_vector(&stream, asd_norm_mean, asd_norm_std, vec)) {
            score_sum += tflm_score_vector(vec);
            t_inf += esp_timer_get_time() - b;
            n_vec++;
        }
    }
    fclose(f);
    if (!n_vec) return -1;
    float score = (float)(score_sum / n_vec);
    if (out_score) *out_score = score;
    /* CSV na stdout — hvataš monitorom: idf.py monitor | tee eval_device.csv */
    printf("EVALCSV,%s,%.8f,%lld,%lld,%d\n", path, score,
           t_feat / 1000, t_inf / 1000, n_vec);
    return 0;
}

int eval_mode_run(void) {
    esp_vfs_fat_mount_config_t cfg = {
        .max_files = 4,
        .format_if_mount_failed = false,
    };
    esp_err_t err = esp_vfs_fat_spiflash_mount_ro(MOUNT_POINT, "storage", &cfg);
    if (err != ESP_OK) {
        ESP_LOGE(TAG, "FAT mount: %s (jesi li upisao fatfs sliku? vidi "
                 "pc/tools/prepare_eval_clips.py)", esp_err_to_name(err));
        return -1;
    }
    DIR *d = opendir(MOUNT_POINT);
    if (!d) { ESP_LOGE(TAG, "opendir"); return -1; }

    printf("EVALCSV,file,score,feat_ms,inf_ms,n_vec\n");
    struct dirent *e;
    int n = 0, fail = 0;
    gamma_calib_t calib;                 /* E6: on-device kalibracija praga */
    gamma_calib_reset(&calib);
    while ((e = readdir(d)) != NULL) {
        const char *dot = strrchr(e->d_name, '.');
        if (!dot || (strcasecmp(dot, ".wav") != 0)) continue;
        char path[300];
        snprintf(path, sizeof(path), MOUNT_POINT "/%s", e->d_name);
        float sc = 0.0f;
        if (score_file(path, &sc) == 0) {
            n++;
            /* normalni klipovi imaju prefiks 'n' (prepare_eval_clips) — samo njih
             * u kalibraciju, kao što bi uređaj radio na terenu (samo normal rad) */
            if (e->d_name[0] == 'n' || e->d_name[0] == 'N')
                gamma_calib_add(&calib, sc);
        } else fail++;
    }
    closedir(d);
    /* E6: prag iz gamma fita normalnih score-ova (momentna metoda + Wilson-Hilferty) */
    float thr = gamma_calib_threshold(&calib, 0.9f);
    printf("E6CALIB,n_normal=%d,thr_device=%.8f,thr_baked=%.8f\n",
           calib.n, thr, (float)ASD_SCORE_THRESHOLD);
    ESP_LOGI(TAG, "eval gotov: %d klipova OK, %d gresaka; E6 prag(dev)=%.5f", n, fail, thr);
    return fail ? -2 : 0;
}
