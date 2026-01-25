#!/bin/bash

#SBATCH --job-name=make_perch_classifier
#SBATCH --cpus-per-task=32
#SBATCH --time=96:00:00
#SBATCH --mem=48G
#SBATCH --nodelist=flor
#SBATCH --output=logs/%x-%j.out

export OMP_NUM_THREADS=$SLURM_CPUS_PER_TASK
export MKL_NUM_THREADS=$SLURM_CPUS_PER_TASK
export OPENBLAS_NUM_THREADS=$SLURM_CPUS_PER_TASK
export NUMEXPR_NUM_THREADS=$SLURM_CPUS_PER_TASK
# prevent accidental oversubscription
export MKL_DYNAMIC=FALSE
export OMP_DYNAMIC=FALSE


uv run classify_script.py