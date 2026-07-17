idf_component_register(
    SRCS "app_main.c" "audio_i2s.c" "features_c.c" "calib_gamma.c" "tflm_infer.cc"
    INCLUDE_DIRS "."
    REQUIRES driver esp_timer
)
