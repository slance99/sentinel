#!/bin/sh

# ── Base paths ────────────────────────────────────────────────────────────────
GEE_BASE="/home/slance/california_rivers/gee_watermask"
OUT_BASE="/home/geomorph/california_rivers/gee_watermask/outputs"

# ── Python script location ────────────────────────────────────────────────────
MAIN="${GEE_BASE}/GEE_watermasks/main.py"

# ── River settings ────────────────────────────────────────────────────────────
poly="$1"
river=$(basename "$poly" .gpkg)
mask_method="Jones"
dataset='sentinel'
network_method="all"        # ← no centerline needed, uses all water pixels
network_path=""             # ← not needed
images="true"
masks="false" #setting to false to make the download go a bit faster, temporary 
dtype="int"
water_level="2"
start_year=2018
end_year=2025

# ── Output directory ──────────────────────────────────────────────────────────
out_root="${OUT_BASE}/yearly_outputs"
mkdir -p "$out_root"

python "${MAIN}" \
    --poly "$poly" \
    --mask_method $mask_method \
    --network_method $network_method \
    --masks $masks \
    --images $images \
    --dataset $dataset \
    --dtype $dtype \
    --water_level $water_level \
    --start 01-01 \
    --end 12-31 \
    --start_year $start_year \
    --end_year $end_year \
    --out "$out_root" \
    --river "$river"

if [ $? -ne 0 ]; then
    echo "ERROR: [$river] Failed — check logs." >&2
    exit 1
fi

echo "[$river] Complete."
