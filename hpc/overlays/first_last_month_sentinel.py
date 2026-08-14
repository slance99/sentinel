# =============================================================================
# sentinel_monthly_overlay.py
#
# For each river section, finds the first and last year of a specific month
# Sentinel water mask, overlays them on the Sentinel image from the first year,
# producing one output image per section per month:
#   {section}_{month}_{first_year}_vs_{last_year}.png
#
# Color scheme (at 50% transparency over Sentinel imagery):
#   Yellow [1.0, 0.9, 0.0] = first year only (water lost)
#   Purple [0.6, 0.2, 0.9] = last year only  (water gained)
#   White  [1.0, 1.0, 1.0] = both years      (persistent water)
#   Transparent             = no water in either year
#
# Usage:
#   python sentinel_monthly_overlay.py <river_name> <outputs_folder>
#   e.g. python sentinel_monthly_overlay.py sacramento red_bluff_colusa
#
# For SLURM:
#   sbatch sentinel_monthly_overlay.sh sacramento red_bluff_colusa
# =============================================================================

import os
import re
import argparse
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.patches import Patch
from pathlib import Path
from collections import defaultdict
import rasterio
from rasterio.warp import reproject, Resampling as WarpResampling
from rasterio.transform import from_bounds


# =============================================================================
# ARGUMENT PARSING
# =============================================================================

parser = argparse.ArgumentParser(
    description="Generate first vs last year monthly Sentinel water mask overlay images"
)
parser.add_argument("river", help="River name e.g. sacramento")
parser.add_argument(
    "outputs",
    nargs="?",
    default=None,
    help="Output folder name e.g. red_bluff_colusa. Defaults to {river}_outputs"
)
args = parser.parse_args()

RIVER   = args.river
OUTPUTS = args.outputs if args.outputs else f"{RIVER}_outputs"


# =============================================================================
# CONFIG
# =============================================================================

# ── Base paths ────────────────────────────────────────────────────────────────
MONTHLY_ROOT = Path("/home/geomorph/california_rivers/gee_watermask/outputs/monthly_outputs")

# ── Output directory ──────────────────────────────────────────────----------------------------------------------------------------────────────
OUTPUT_DIR = Path("/home/geomorph/california_rivers/gee_watermask/outputs/overlays/monthly_overlays")
OVERLAY_ALPHA = 0.5
DPI           = 150

# ── Month names for labels ────────────────────────────────────────────────────
MONTH_NAMES = {
    '01': 'January',   '02': 'February',  '03': 'March',
    '04': 'April',     '05': 'May',        '06': 'June',
    '07': 'July',      '08': 'August',     '09': 'September',
    '10': 'October',   '11': 'November',   '12': 'December'
}

# ── Colors ────────────────────────────────────────────────────────────────────
COLOR_LOST       = [1.0, 0.9, 0.0]  # yellow  — water lost by last year
COLOR_GAINED     = [0.6, 0.2, 0.9]  # purple  — water gained by last year
COLOR_PERSISTENT = [1.0, 1.0, 1.0]  # white   — water in both years


# =============================================================================
# SETUP
# =============================================================================

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

print(f"River:          {RIVER}")
print(f"Outputs:        {OUTPUTS}")
print(f"Monthly outputs from: {MONTHLY_ROOT}")
print(f"Output to:      {OUTPUT_DIR}\n")

if not MONTHLY_ROOT.exists():
    print(f"ERROR: Monthly outputs directory does not exist: {MONTHLY_ROOT}")
    raise SystemExit(1)


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def parse_year_month_from_mask(path):
    """
    Extract year and month from mask filename.
    e.g. sacramento_32_2018_01_01_2018_01_31_mask.tif -> (2018, '01')
    """
    match = re.search(r'_(\d{4})_(\d{2})_\d{2}_\d{4}_\d{2}_\d{2}_mask', path.stem)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def parse_year_month_from_image(path):
    """
    Extract year and month from image filename.
    e.g. sacramento_32_2018_01_01_2018_01_31_full_image.tif -> (2018, '01')
    """
    match = re.search(r'_(\d{4})_(\d{2})_\d{2}_\d{4}_\d{2}_\d{2}_full_image', path.stem)
    if match:
        return int(match.group(1)), match.group(2)
    return None, None


def load_sentinel_rgb(image_path):
    """
    Load a Sentinel image as an RGB array normalized to 0-1.
    Sentinel bands: 0=uBlue, 1=Blue, 2=Green, 3=Red, 4=NIR, 5=SWIR1, 6=SWIR2, 7=BQA
    Using Red=4, Green=3, Blue=2 for natural color composite.
    """
    with rasterio.open(image_path) as src:
        r = src.read(4).astype(float)  # Red
        g = src.read(3).astype(float)  # Green
        b = src.read(2).astype(float)  # Blue
        transform = src.transform
        crs       = src.crs
        bounds    = src.bounds
        out_shape = (src.height, src.width)

    rgb = np.stack([r, g, b], axis=-1)
    p2, p98 = np.percentile(rgb[rgb > 0], (2, 98)) if np.any(rgb > 0) else (0, 1)
    rgb = np.clip((rgb - p2) / (p98 - p2 + 1e-10), 0, 1)

    return rgb, out_shape, transform, crs, bounds


def load_mask_aligned(mask_path, target_shape, bounds, target_crs):
    """
    Load a water mask and reproject/resample it to exactly match the
    target image's shape and extent.
    """
    dst_transform = from_bounds(
        bounds.left, bounds.bottom,
        bounds.right, bounds.top,
        target_shape[1], target_shape[0]
    )

    with rasterio.open(mask_path) as src:
        aligned = np.zeros(target_shape, dtype=np.uint8)
        reproject(
            source=rasterio.band(src, 1),
            destination=aligned,
            src_transform=src.transform,
            src_crs=src.crs,
            dst_transform=dst_transform,
            dst_crs=target_crs,
            resampling=WarpResampling.nearest,
        )
    return aligned > 0


def make_overlay_rgba(first_mask, last_mask, alpha=OVERLAY_ALPHA):
    """
    Build an RGBA overlay from two binary water masks.
    """
    h, w = first_mask.shape
    overlay = np.zeros((h, w, 4), dtype=np.float32)

    overlay[first_mask & ~last_mask] = COLOR_LOST       + [alpha]
    overlay[~first_mask & last_mask] = COLOR_GAINED     + [alpha]
    overlay[first_mask & last_mask]  = COLOR_PERSISTENT + [alpha]

    stats = {
        "lost":       int(np.sum(first_mask & ~last_mask)),
        "gained":     int(np.sum(~first_mask & last_mask)),
        "persistent": int(np.sum(first_mask & last_mask)),
    }

    return overlay, stats


def save_overlay_image(sentinel_rgb, overlay, stats, bounds,
                       section_name, month, first_year, last_year,
                       output_path):
    """
    Compose and save a single overlay image with Sentinel background.
    """
    month_name = MONTH_NAMES.get(month, month)

    fig, ax = plt.subplots(figsize=(14, 10))
    fig.patch.set_facecolor("black")
    fig.suptitle(
        f"{section_name.replace('_', ' ')}  —  {month_name} {first_year} vs {month_name} {last_year}",
        fontsize=16, fontweight="bold", color="white"
    )

    ax.set_facecolor("black")

    ax.imshow(
        sentinel_rgb,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
        origin="upper",
        aspect="auto",
        interpolation="bilinear",
        zorder=1
    )

    ax.imshow(
        overlay,
        extent=[bounds.left, bounds.right, bounds.bottom, bounds.top],
        origin="upper",
        aspect="auto",
        interpolation="nearest",
        zorder=2
    )

    ax.set_xlim(bounds.left,  bounds.right)
    ax.set_ylim(bounds.bottom, bounds.top)
    ax.set_xlabel("Longitude", color="white", fontsize=9)
    ax.set_ylabel("Latitude",  color="white", fontsize=9)
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_edgecolor("white")

    legend_elements = [
        Patch(facecolor=COLOR_LOST, alpha=OVERLAY_ALPHA,
              label=f"Water in {month_name} {first_year} only (lost by {last_year}) ({stats['lost']:,} px)"),
        Patch(facecolor=COLOR_GAINED, alpha=OVERLAY_ALPHA,
              label=f"Water in {month_name} {last_year} only (gained since {first_year}) ({stats['gained']:,} px)"),
        Patch(facecolor=COLOR_PERSISTENT, alpha=OVERLAY_ALPHA,
              label=f"Persistent water ({stats['persistent']:,} px)"),
        Patch(facecolor=[0.05, 0.05, 0.05], edgecolor="white",
              label="No water either year (Sentinel imagery shows through)"),
    ]
    ax.legend(
        handles=legend_elements,
        loc="upper right",
        facecolor="black",
        edgecolor="white",
        labelcolor="white",
        framealpha=0.9,
        fontsize=9
    )

    plt.tight_layout()
    plt.savefig(output_path, facecolor="black", dpi=DPI, bbox_inches="tight")
    plt.close(fig)
    print(f"  Saved -> {output_path.name}")


# =============================================================================
# MAIN LOOP
# =============================================================================

# ── Find all river section folders ───────────────────────────────────────────
section_dirs = sorted([
    d for d in MONTHLY_ROOT.iterdir()
    if d.is_dir() and re.match(rf'{RIVER}_\d+$', d.name)
])

if not section_dirs:
    print(f"ERROR: No section folders found matching '{RIVER}_N' in {MONTHLY_ROOT}")
    raise SystemExit(1)

print(f"Found {len(section_dirs)} section folders\n")

for section_dir in section_dirs:
    section_name = section_dir.name
    print(f"{'='*50}")
    print(f"Processing: {section_name}")

    mask_dir  = section_dir / "mask"
    image_dir = section_dir / "image"

    if not mask_dir.exists():
        print(f"  Skipping — no mask folder found")
        continue

    if not image_dir.exists():
        print(f"  Skipping — no image folder found")
        continue

    # ── Collect masks by month and year ──────────────────────────────────
    # Structure: masks_by_month[month][year] = path
    masks_by_month = defaultdict(dict)
    for mask_path in sorted(mask_dir.glob("*.tif")):
        year, month = parse_year_month_from_mask(mask_path)
        if year is not None and month is not None:
            masks_by_month[month][year] = mask_path

    # ── Collect images by month and year ──────────────────────────────────
    images_by_month = defaultdict(dict)
    for image_path in sorted(image_dir.glob("*.tif")):
        year, month = parse_year_month_from_image(image_path)
        if year is not None and month is not None:
            images_by_month[month][year] = image_path

    if not masks_by_month:
        print(f"  Skipping — no masks found")
        continue

    print(f"  Found masks for months: {sorted(masks_by_month.keys())}")

    # ── Process each month ────────────────────────────────────────────────
    for month in sorted(masks_by_month.keys()):
        month_name = MONTH_NAMES.get(month, month)
        year_dict  = masks_by_month[month]
        years      = sorted(year_dict.keys())

        print(f"  -- {month_name}: available years {years}")

        if len(years) < 2:
            print(f"    Skipping — need at least 2 years, found {len(years)}")
            continue

        first_year = years[0]
        last_year  = years[-2]  # second to last year

        print(f"    Comparing: {first_year} vs {last_year}")

        # ── Output path ───────────────────────────────────────────────────
        out_path = OUTPUT_DIR / f"{section_name}_{month}_{first_year}_vs_{last_year}.png"

        if out_path.exists():
            print(f"    Skipping — output already exists")
            continue

        # ── Find background image ─────────────────────────────────────────
        bg_image_path = images_by_month[month].get(first_year)
        if bg_image_path is None:
            print(f"    WARNING: no image for {month_name} {first_year}, trying last year")
            bg_image_path = images_by_month[month].get(last_year)
        if bg_image_path is None:
            print(f"    Skipping — no images found for {month_name}")
            continue

        try:
            print(f"    Loading Sentinel background: {bg_image_path.name}")
            sentinel_rgb, out_shape, sentinel_transform, sentinel_crs, bounds = \
                load_sentinel_rgb(bg_image_path)

            first_mask = load_mask_aligned(
                year_dict[first_year], out_shape, bounds, sentinel_crs
            )
            last_mask = load_mask_aligned(
                year_dict[last_year], out_shape, bounds, sentinel_crs
            )

            overlay, stats = make_overlay_rgba(first_mask, last_mask)

            save_overlay_image(
                sentinel_rgb, overlay, stats, bounds,
                section_name, month, first_year, last_year,
                output_path=out_path
            )

            del sentinel_rgb, first_mask, last_mask, overlay

        except Exception as e:
            print(f"    ERROR: {e}")
            continue

print("\nAll done!")
