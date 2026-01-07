import numpy as np
from perch_hoplite.zoo import model_configs, zoo_interface
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Configuration
NUM_THREADS = 8
NUM_SAMPLES = 100


def embed_audio(model: zoo_interface.EmbeddingModel, sample_id):
    """Embed a single audio sample."""
    audio = np.random.random(32000 * 5)
    start = time.time()
    e = model.embed(audio)
    elapsed = time.time() - start
    return sample_id, e.embeddings.shape if e.embeddings else None, elapsed


def main():
    print("Loading model...")
    model = model_configs.load_model_by_name("perch_v2")
    print(
        f"Model loaded. Starting {NUM_SAMPLES} embeddings with {NUM_THREADS} threads...\n"
    )

    overall_start = time.time()

    with ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # Submit all tasks
        futures = [executor.submit(embed_audio, model, i) for i in range(NUM_SAMPLES)]

        # Collect results
        times = []
        for future in as_completed(futures):
            sample_id, shape, elapsed = future.result()
            # first 10 it is tuning
            if sample_id < 10:
                continue
            times.append(elapsed)
            print(f"Sample {sample_id}: {shape} - {elapsed:.4f}s")

    overall_elapsed = time.time() - overall_start

    print(f"\n{'=' * 60}")
    print(f"Total time: {overall_elapsed:.4f}s")
    print(f"Average time per embedding: {np.mean(times):.4f}s")
    print(f"Min time: {np.min(times):.4f}s")
    print(f"Max time: {np.max(times):.4f}s")
    print(f"Throughput: {NUM_SAMPLES / overall_elapsed:.2f} embeddings/second")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    main()
