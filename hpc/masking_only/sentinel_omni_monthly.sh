#!/bin/bash
#SBATCH --job-name=sentinel_omni_monthly
#SBATCH --output=/home/geomorph/california_rivers/gee_watermask/hpc/masking_only/logs/omni_monthly_%A.out
#SBATCH --error=/home/geomorph/california_rivers/gee_watermask/hpc/masking_only/logs/omni_monthly_%A.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=4
#SBATCH --time=48:00:00
#SBATCH --mem=32G
#SBATCH --gres=gpu:1

export PYTHONUNBUFFERED=1

source ~/miniconda3/etc/profile.d/conda.sh
conda activate omni_env

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Usage: sbatch sentinel_omni_monthly.sh <river> <gpkgs_folder>"
    echo "Example: sbatch sentinel_omni_monthly.sh sacramento red_bluff_colusa_gpkgs"
    exit 1
fi

RIVER=$1
GPKGS=$2

SCRIPT_BASE="/home/geomorph/california_rivers/gee_watermask/hpc/masking_only"
python "${SCRIPT_BASE}/sentinel_omni_monthly.py" "$RIVER" "$GPKGS"
