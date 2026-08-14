#!/bin/bash
#SBATCH --job-name=sentinel_yr
#SBATCH --output=logs/sent_overlay_%A.out
#SBATCH --error=logs/sent_overlay_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G

# ── Base paths ────────────────────────────────────────────────────────────────
# Where the scripts live
SCRIPT_BASE="/home/slance/california_rivers/gee_watermask/hpc/overlays"
# Where the data (gpkgs, outputs) live
DATA_BASE="home/geomorph/slance/gee_watermask/outputs/yearly_outputs"

# ── Activate conda environment ────────────────────────────────────────────────
source ~/miniconda3/etc/profile.d/conda.sh
conda activate watermask_39

# ── Run the Python orchestrator ───────────────────────────────────────────────
python "${SCRIPT_BASE}/run_all_yr.py" "$GPKG_FOLDER"
