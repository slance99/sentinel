#!/bin/bash
#SBATCH --job-name=sentinel_doubles
#SBATCH --output=/home/geomorph/california_rivers/gee_watermask/hpc/first_last/logs/sentinel_doubles_%A.out
#SBATCH --error=/home/geomorph/california_rivers/gee_watermask/hpc/first_last/logs/sentinel_doubles_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=8:00:00
#SBATCH --mem=32G

export PYTHONUNBUFFERED=1

source ~/miniconda3/etc/profile.d/conda.sh
conda activate watermask_39

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: sbatch sentinel_doubles.sh <river> <gpkg_folder>"
    echo "Example: sbatch sentinel_doubles.sh sacramento red_bluff_colusa_gpkgs"
    exit 1
fi

RIVER=$1
GPKGS=$2

SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc/first_last"
python "${SCRIPT_BASE}/fldm_rotated.py" "$RIVER" "$GPKGS"
