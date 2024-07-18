import collections
from etils import epath
import numpy as np
from tqdm import tqdm
import logging
import tempfile

from chirp.inference.search import bootstrap
from chirp.inference.classify import classify
from chirp.inference.classify import data_lib
import polars as pl


def main(
    embeddings_path: epath.PathLike,
    labeled_data_path: epath.PathLike,
    output_path: epath.PathLike,
):
    bootstrap_config = bootstrap.BootstrapConfig.load_from_embedding_path(
        embeddings_path=embeddings_path,
        annotated_path=labeled_data_path,
    )

    project_state = bootstrap.BootstrapState(bootstrap_config)

    sample_rate = bootstrap_config.model_config["sample_rate"]

    merged = data_lib.MergedDataset.from_folder_of_folders(
        base_dir=labeled_data_path,
        embedding_model=project_state.embedding_model,
        time_pooling="mean",
        load_audio=False,
        target_sample_rate=sample_rate,
        audio_file_pattern="*wav",
        embedding_config_hash=bootstrap_config.embedding_config_hash(),
    )

    lbl_counts = np.sum(merged.data["label_hot"], axis=0)
    logging.info("num classes :", (lbl_counts > 0).sum())
    logging.info("mean ex / class :", lbl_counts.sum() / (lbl_counts > 0).sum())
    logging.info("min ex / class :", (lbl_counts + (lbl_counts == 0) * 1e6).min())

    train_ratio = 0.9
    train_examples_per_class = None

    num_seeds = 3

    # Classifier training hyperparams.
    # These should be good defaults.
    batch_size = 32
    num_epochs = 128
    num_hiddens = -1
    learning_rate = 1e-3

    metrics = collections.defaultdict(list)
    for seed in tqdm(range(num_seeds)):
        if num_hiddens > 0:
            model = classify.get_two_layer_model(
                num_hiddens, merged.embedding_dim, merged.num_classes, True
            )
        else:
            model = classify.get_linear_model(merged.embedding_dim, merged.num_classes)
        run_metrics = classify.train_embedding_model(
            model,
            merged,
            train_ratio,
            train_examples_per_class,
            num_epochs,
            seed,
            batch_size,
            learning_rate,
        )
        metrics["acc"].append(run_metrics.top1_accuracy)
        metrics["auc_roc"].append(run_metrics.auc_roc)
        metrics["cmap"].append(run_metrics.cmap_value)
        metrics["maps"].append(run_metrics.class_maps)
        metrics["test_logits"].append(run_metrics.test_logits)

    mean_acc = np.mean(metrics["acc"])
    mean_auc = np.mean(metrics["auc_roc"])
    mean_cmap = np.mean(metrics["cmap"])

    logging.info(f"acc:{mean_acc:5.2f}, auc_roc:{mean_auc:5.2f}, cmap:{mean_cmap:5.2f}")
    for lbl, auc in zip(merged.labels, run_metrics.class_maps):
        if np.isnan(auc):
            continue
    logging.info(f"\n{lbl:8s}, auc_roc:{auc:5.2f}")

    output_filepath = epath.Path(output_path)

    embeddings_ds = project_state.create_embeddings_dataset(shuffle_files=True)

    with tempfile.NamedTemporaryFile(suffix=".csv") as f:
        csv_output_path = f.name
        classify.write_inference_csv(
            embeddings_ds=embeddings_ds,
            model=model,
            labels=merged.labels,
            output_filepath=csv_output_path,
            embedding_hop_size_s=bootstrap.embedding_hop_size_s,
            include_classes=[],
            exclude_classes=[],
        )

        output = pl.scan_csv(csv_output_path)
        output.sink_parquet(
            path=output_filepath,
            row_group_size=100_000,
        )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--embeddings_path", type=epath.Path)
    parser.add_argument("--labeled_data_path", type=epath.Path)
    parser.add_argument("--output_path", type=epath.Path)
    args = parser.parse_args()

    main(args.embeddings_path, args.labeled_data_path, args.output_path)
