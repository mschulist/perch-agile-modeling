#!/usr/bin/env bash
#SBATCH --job-name=perch_embed
#SBATCH --cpus-per-task=16
#SBATCH --mem=32G
#SBATCH --nodelist=alice
#SBATCH --gres=gpu:1
#SBATCH --output=logs/%x-%j.out
#SBATCH --error=logs/%x-%j.err

set -e

echo "Running on $(hostname)"
nvidia-smi

. ~/miniconda3/etc/profile.d/conda.sh
conda activate perch_v2_embed

which python
echo "CONDA ENV: $CONDA_DEFAULT_ENV"

LD_LIBRARY_PATH="$CONDA_PREFIX/lib:$LD_LIBRARY_PATH" python embed_script.py
