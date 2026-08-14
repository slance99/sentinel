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
network_method="all"
images="true"
masks="true"
dtype="int"
water_level="2"
start_year=2018
end_year=2025

# ── Output directory ──────────────────────────────────────────────────────────
out_root="${OUT_BASE}/monthly_outputs"
mkdir -p "$out_root"

# ── Helper: returns the number of days in a given month/year ─────────────────
days_in_month() {
    month=$1; year=$2
    case $month in
        01|03|05|07|08|10|12) echo 31 ;;
        04|06|09|11)          echo 30 ;;
        02)
            if [ "$(expr $year % 400)" = "0" ]; then echo 29
            elif [ "$(expr $year % 100)" = "0" ]; then echo 28
            elif [ "$(expr $year % 4)" = "0" ]; then echo 29
            else echo 28
            fi ;;
    esac
}

# ── Main loop: one call per month per year ────────────────────────────────────
for year in $(seq $start_year $end_year); do
    for month in $(seq -w 1 12); do

        last_day=$(days_in_month $month $year)
        start="${month}-01"
        end="${month}-${last_day}"

        echo "[$river] Processing: Year=$year | Month=$month" 

	# ── Skip if image already exists for this month ───────────────────────────────
	start_text="${year}_${month}_01"
	end_text="${year}_${month}_${last_day}"
	image_check="${out_root}/${river}/image/${river}_${start_text}_${end_text}_full_image.tif"

	if [ -f "$image_check" ]; then
    		echo "[$river] Skipping $year-$month — image already exists"
    		continue
	fi

        python "${MAIN}" \
            --poly "$poly" \
            --mask_method $mask_method \
            --network_method $network_method \
            --masks $masks \
            --images $images \
            --dataset $dataset \
            --dtype $dtype \
            --water_level $water_level \
            --start $start \
            --end $end \
            --start_year $year \
            --end_year $year \
            --out "$out_root" \
            --river "$river"

        if [ $? -ne 0 ]; then
            echo "ERROR: [$river] Failed on $year-$month — continuing." >&2
        fi

    done
done

echo "[$river] Complete."
