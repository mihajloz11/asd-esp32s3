idf_component_register(
    SRCS "app_main.c" "audio_i2s.c" "features_c.c" "calib_gamma.c" "tflm_infer.cc"
         "eval_mode.c" "mic_test.c"
    INCLUDE_DIRS "."
    REQUIRES driver esp_timer fatfs
)

# Eval build bez tastera:  set ASD_EVAL_MODE=1  pa idf.py build
if(DEFINED ENV{ASD_EVAL_MODE})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_EVAL_MODE)
endif()

# Mic bring-up build:  set ASD_MIC_TEST=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_MIC_TEST})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_MIC_TEST)
endif()
