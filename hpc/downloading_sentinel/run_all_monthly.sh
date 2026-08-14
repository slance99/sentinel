#!/bin/bash
#SBATCH --job-name=watermask_monthly
#SBATCH --output=/home/geomorph/california_rivers/gee_watermask/hpc/logs/watermask_monthly_%A.out
#SBATCH --error=/home/geomorph/california_rivers/gee_watermask/hpc/logs/watermask_monthly_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --time=96:00:00
#SBATCH --mem=16G

export PYTHONUNBUFFERED=1

source ~/miniconda3/etc/profile.d/conda.sh
conda activate watermask_39

if [ -z "$1" ]; then
    echo "Usage: sbatch run_all_monthly.sh <gpkg_folder>"
    echo "Example: sbatch run_all_monthly.sh red_bluff_colusa_gpkgs"
    exit 1
fi

GPKG_FOLDER=$1
GPKG_DIR="/home/geomorph/california_rivers/naip/gpkgs/all/${GPKG_FOLDER}"
SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc/downloading_sentinel"

# ── Loop through all gpkgs sequentially ──────────────────────────────────────
for gpkg in $(ls ${GPKG_DIR}/*.gpkg | sort); do
    echo "Starting: $(basename $gpkg)"
    bash "${SCRIPT_BASE}/run_single_river_monthly.sh" "$gpkg"
    echo "Done: $(basename $gpkg)"
done

echo "All rivers complete."
