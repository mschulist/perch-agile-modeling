from typing import Callable

# from perch_hoplite.zoo import model_configs
import onnxruntime as ort
import numpy as np
from datetime import datetime as dt

from tqdm import tqdm


SAMPLE_RATE = 32000
WINDOW_SIZE_S = 5

WARMUP = 10

onnx_model_path = "/home/mschulist/perch-agile-modeling/perch-analyzer/data/models/perch_v2_no_dft.onnx"

# tf_model = model_configs.load_model_by_name("perch_v2")

sess_opts = ort.SessionOptions()
sess_opts.intra_op_num_threads = 16
sess_opts.inter_op_num_threads = 1

session = ort.InferenceSession(
    onnx_model_path, sess_opts, providers=["CUDAExecutionProvider"]
)

print(ort.get_available_providers())


def embed_tf_model(audio_batch: np.ndarray):
    return tf_model.batch_embed(audio_batch)


def embed_onnx_model(audio_batch: np.ndarray):
    return session.run(None, {"inputs": audio_batch})


def generate_audio(n_windows: int):
    return np.random.uniform(0, 1, (n_windows, WINDOW_SIZE_S * SAMPLE_RATE)).astype(
        np.float32
    )


def run_benchmark(model: Callable, batch_size: int, n_batches: int):
    for _ in tqdm(range(WARMUP)):
        model(generate_audio(batch_size))

    times = []
    for _ in tqdm(range(n_batches)):
        audio = generate_audio(batch_size)
        before = dt.now()
        model(audio)
        times.append(dt.now() - before)

    return np.mean(times)


batch_size = 50
print(
    f"onnx average time per batch of {batch_size} recordings",
    run_benchmark(embed_onnx_model, batch_size, 25),
)
# print(
#     f"tf average time per batch of {batch_size} recordings",
#     run_benchmark(embed_tf_model, batch_size, 25),
# )
