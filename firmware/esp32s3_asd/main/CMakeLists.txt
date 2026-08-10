idf_component_register(
    SRCS "app_main.c" "audio_i2s.c" "audio_quality_state.c" "features_c.c" "calib_gamma.c" "tflm_infer.cc"
         "eval_mode.c" "mic_test.c" "ina226.c" "ina226_test.c" "live_capture.c" "live_adapt.c"
         "psd_features_c.c" "psd_live.c" "psd_verify.c"
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

# INA226 bring-up build:  set ASD_INA_TEST=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_INA_TEST})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_INA_TEST)
endif()

# Zivi klip + score + snimak:  set ASD_LIVE_CAPTURE=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_LIVE_CAPTURE})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_LIVE_CAPTURE)
endif()

# Prilagodjavanje praga okruzenju:  set ASD_LIVE_ADAPT=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_LIVE_ADAPT})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_LIVE_ADAPT)
endif()

# Samostalni PSD detektor (finalni model):  set ASD_PSD_LIVE=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_PSD_LIVE})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_PSD_LIVE)
endif()

# PC<->uredjaj provjera PSD front-enda:  set ASD_PSD_VERIFY=1  pa idf.py reconfigure build
if(DEFINED ENV{ASD_PSD_VERIFY})
    target_compile_definitions(${COMPONENT_LIB} PRIVATE ASD_PSD_VERIFY)
endif()
