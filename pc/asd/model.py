"""AE modeli: baseline (DCASE) + AE-tiny familija za Pareto sweep.

Baseline: 640 -> [128 x4] -> 8 -> [128 x4] -> 640, Dense+BN+ReLU (~267k param).
AE-tiny: parametrizovano width/depth/bottleneck (+ opciono manji input za F=64/P=3).

BatchNorm se pri TFLite konverziji fuzuje u Dense — na uređaju ostaju samo
FullyConnected + Relu (+ Quantize/Dequantize za int8).
"""
from __future__ import annotations

import tensorflow as tf
from tensorflow.keras import layers


def build_ae(input_dim: int = 640, width: int = 128, depth: int = 4, bottleneck: int = 8) -> tf.keras.Model:
    inp = layers.Input(shape=(input_dim,), name="input")
    x = inp
    for i in range(depth):
        x = layers.Dense(width, name=f"enc_{i}")(x)
        x = layers.BatchNormalization(name=f"enc_bn_{i}")(x)
        x = layers.ReLU(name=f"enc_relu_{i}")(x)
    x = layers.Dense(bottleneck, name="bottleneck")(x)
    x = layers.BatchNormalization(name="bn_bottleneck")(x)
    x = layers.ReLU(name="relu_bottleneck")(x)
    for i in range(depth):
        x = layers.Dense(width, name=f"dec_{i}")(x)
        x = layers.BatchNormalization(name=f"dec_bn_{i}")(x)
        x = layers.ReLU(name=f"dec_relu_{i}")(x)
    out = layers.Dense(input_dim, name="output")(x)
    m = tf.keras.Model(inp, out, name=f"ae_w{width}d{depth}b{bottleneck}")
    m.compile(optimizer=tf.keras.optimizers.Adam(1e-3), loss="mse")
    return m


# Pareto sweep konfiguracije (E2). input_dim=640 osim *mel64 varijanti.
SWEEP = {
    "baseline":  dict(width=128, depth=4, bottleneck=8),
    "tiny64":    dict(width=64,  depth=2, bottleneck=8),
    "tiny32":    dict(width=32,  depth=2, bottleneck=8),
    "tiny16":    dict(width=16,  depth=2, bottleneck=4),
    "tiny32b4":  dict(width=32,  depth=2, bottleneck=4),
}
