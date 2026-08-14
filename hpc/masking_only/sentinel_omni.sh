#!/bin/bash
#SBATCH --job-name=sentinel_omni
#SBATCH --output=/home/geomorph/california_rivers/gee_watermask/hpc/logs/sentinel_omni_%A.out
#SBATCH --error=/home/geomorph/california_rivers/gee_watermask/hpc/logs/sentinel_omni_%A.err
#SBATCH --ntasks=1
#SBATCH --mail-type=END
#SBATCH --cpus-per-task=4
#SBATCH --time=24:00:00
#SBATCH --mem=32G
#SBATCH --gres=gpu:1     # ← request GPU for cuda mosaic device

export PYTHONUNBUFFERED=1

# ── Activate conda environment ────────────────────────────────────────────────
source ~/miniconda3/etc/profile.d/conda.sh
conda activate omni_env

# ── Check arguments ───────────────────────────────────────────────────────────
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: sbatch sentinel_omni.sh <river> <gpkgs_folder>"
    echo "Example: sbatch sentinel_omni.sh sacramento red_bluff_colusa_gpkgs"
    exit 1
fi

RIVER=$1
GPKGS=$2

# ── Run the masking script ────────────────────────────────────────────────────
SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc/masking_only"
python "${SCRIPT_BASE}/sentinel_omni.py" "$RIVER" "$GPKGS"
