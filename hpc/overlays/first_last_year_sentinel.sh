#!/bin/bash
#SBATCH --job-name=sentinel_overlay
#SBATCH --output=/home/geomorph/california_rivers/gee_watermask/hpc/overlays/logs/sentinel_overlay_%A.out
#SBATCH --error=/home/geomorph/california_rivers/gee_watermask/hpc/overlays/logs/sentinel_overlay_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=16G

export PYTHONUNBUFFERED=1

# ── Activate conda environment ────────────────────────────────────────────────
source ~/miniconda3/etc/profile.d/conda.sh
conda activate watermask_39

# ── Check arguments ───────────────────────────────────────────────────────────
if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: sbatch sentinel_overlay.sh <river> <outputs_folder>"
    echo "Example: sbatch sentinel_overlay.sh sacramento red_bluff_colusa"
    exit 1
fi

RIVER=$1
OUTPUTS=$2

# ── Run the overlay script ────────────────────────────────────────────────────
SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc/overlays"
python "${SCRIPT_BASE}/first_last_year_sentinel.py" "$RIVER" "$OUTPUTS"
