#include "tflm_infer.h"
#define ASD_INCLUDE_MODEL_BLOB
#include "model_data.h"

#include "tensorflow/lite/micro/micro_interpreter.h"
#include "tensorflow/lite/micro/micro_mutable_op_resolver.h"
#include "tensorflow/lite/schema/schema_generated.h"

#include <math.h>

#include "esp_heap_caps.h"
#include "esp_log.h"

static const char *TAG = "tflm";

/* Arena: kreni 512 KB u PSRAM-u, očitaj arena_used pa smanji (rizik C5).
 * Za "sve u SRAM" varijantu (AE-tiny, E4/E5): -DASD_ARENA_INTERNAL + manja arena. */
#ifndef ASD_ARENA_SIZE
#define ASD_ARENA_SIZE (512 * 1024)
#endif

static tflite::MicroInterpreter *interp;
static TfLiteTensor *in_t, *out_t;
static uint8_t *arena;

extern "C" int tflm_init(void) {
    const tflite::Model *model = tflite::GetModel(asd_model_tflite);
    if (model->version() != TFLITE_SCHEMA_VERSION) {
        ESP_LOGE(TAG, "schema mismatch: %lu", (unsigned long)model->version());
        return -1;
    }
#ifdef ASD_ARENA_INTERNAL
    arena = (uint8_t *)heap_caps_malloc(ASD_ARENA_SIZE, MALLOC_CAP_INTERNAL | MALLOC_CAP_8BIT);
#else
    arena = (uint8_t *)heap_caps_malloc(ASD_ARENA_SIZE, MALLOC_CAP_SPIRAM | MALLOC_CAP_8BIT);
#endif
    if (!arena) { ESP_LOGE(TAG, "arena alloc failed"); return -2; }

    /* Samo opovi koje dense AE koristi — manji binar (plan 5.3) */
    static tflite::MicroMutableOpResolver<4> resolver;
    resolver.AddFullyConnected();
    resolver.AddRelu();
    resolver.AddQuantize();
    resolver.AddDequantize();

    static tflite::MicroInterpreter static_interp(model, resolver, arena, ASD_ARENA_SIZE);
    interp = &static_interp;
    if (interp->AllocateTensors() != kTfLiteOk) {
        ESP_LOGE(TAG, "AllocateTensors failed");
        return -3;
    }
    in_t = interp->input(0);
    out_t = interp->output(0);
    ESP_LOGI(TAG, "arena used: %u B", (unsigned)interp->arena_used_bytes());
    return 0;
}

extern "C" size_t tflm_arena_used(void) {
    return interp ? interp->arena_used_bytes() : 0;
}

extern "C" float tflm_score_vector(const float *vec) {
    const float si = in_t->params.scale;
    const int zi = in_t->params.zero_point;
    const float so = out_t->params.scale;
    const int zo = out_t->params.zero_point;
    const int dim = in_t->dims->data[in_t->dims->size - 1];

    int8_t *ip = in_t->data.int8;
    for (int i = 0; i < dim; i++) {
        int q = (int)lroundf(vec[i] / si) + zi;
        ip[i] = (int8_t)(q < -128 ? -128 : (q > 127 ? 127 : q));
    }
    if (interp->Invoke() != kTfLiteOk) return -1.0f;

    const int8_t *op = out_t->data.int8;
    float mse = 0.0f;
    for (int i = 0; i < dim; i++) {
        float rec = ((int)op[i] - zo) * so;
        float d = vec[i] - rec;
        mse += d * d;
    }
    return mse / (float)dim;
}
