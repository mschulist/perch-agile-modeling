#!/bin/bash
#SBATCH --job-name=perch-gui
#SBATCH --nodelist=flor
#SBATCH --mem=32G
#SBATCH --time=3-00:00:00
#SBATCH --output=perch-gui-%j.log

cd /home/mschulist/perch-agile-modeling/perch-analyzer
uv run perch-analyzer gui --data_dir data --host 0.0.0.0 --port 8001