#!/bin/bash
#SBATCH --job-name=sentinel_yr
#SBATCH --output=logs/sentinel_%A.out
#SBATCH --error=logs/sentinel_yr_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=72:00:00
#SBATCH --mem=64G

# ── Base paths ────────────────────────────────────────────────────────────────
# Where the scripts live
SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc"
# Where the data (gpkgs, outputs) live
DATA_BASE="home/geomorph/california_rivers/naip/gpkgs/all"

# ── Activate conda environment ────────────────────────────────────────────────
source ~/miniconda3/etc/profile.d/conda.sh
conda activate watermask_39

# ── Get gpkg folder from command line argument ────────────────────────────────
if [ -z "$1" ]; then
    echo "Usage: sbatch run_all_yr.sh <gpkg_folder>"
    echo "Example: sbatch run_all_yr.sh rbc_small_gpkgs"
    exit 1
fi

GPKG_FOLDER=$1


# ── Run the Python orchestrator ───────────────────────────────────────────────
export PYTHONUNBUFFERED=1
python "${SCRIPT_BASE}/run_all_yr.py" "$GPKG_FOLDER"
