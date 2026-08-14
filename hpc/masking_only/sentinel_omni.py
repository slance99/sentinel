# =============================================================================
# sentinel_watermask_omni.py
#
# Runs OmniWaterMask on existing Sentinel-2 yearly composite images
# for a set of GeoPackage AOIs.
#
# Assumes Sentinel images already downloaded to:
#   SENTINEL_ROOT/{section}/image/{section}_{year}_01_01_{year}_12_31_full_image.tif
#
# Outputs water masks to:
#   SENTINEL_ROOT/{section}/omni_mask/{section}_{year}_omni_mask.tif
#
# Usage:
#   python sentinel_watermask_omni.py <river> <gpkgs>
#   e.g. python sentinel_watermask_omni.py sacramento red_bluff_colusa_gpkgs
#
# For SLURM:
#   sbatch sentinel_omni.sh sacramento red_bluff_colusa_gpkgs
# =============================================================================

from pathlib import Path
from collections import defaultdict
import re
import geopandas as gpd
import fiona
import rasterio
from rasterio.mask import mask as rio_mask
from shapely.geometry import mapping, box
import numpy as np
from omniwatermask import make_water_mask
from scipy.ndimage import binary_fill_holes
from skimage.morphology import closing, opening, disk, remove_small_objects
from skimage.measure import label, regionprops
import builtins
import argparse

# =============================================================================
# ARGUMENT PARSING
# =============================================================================

parser = argparse.ArgumentParser(
    description="Run OmniWaterMask on existing Sentinel-2 yearly composites"
)
parser.add_argument("river", help="River name e.g. sacramento")
parser.add_argument("gpkgs", help="GPKG folder name e.g. red_bluff_colusa_gpkgs")
args = parser.parse_args()

RIVER = args.river
GPKGS = args.gpkgs

# =============================================================================
# CONFIG
# =============================================================================

# ── Input paths ───────────────────────────────────────────────────────────────
GPKG_DIR      = Path(f"/home/geomorph/california_rivers/naip/gpkgs/all/{GPKGS}_gpkgs/")
SENTINEL_ROOT = Path("/home/geomorph/slance/gee_watermask/outputs/yearly_outputs")

# ── Processing settings ───────────────────────────────────────────────────────
# Sentinel-2 is 10m resolution vs NAIP ~0.6m so cleaning parameters are scaled
# down since each pixel represents a much larger area on the ground
CLOSING_RADIUS = 2    # NAIP=4  — closes small gaps in water bodies
OPENING_RADIUS = 1    # NAIP=2  — removes small noise speckles
MIN_BLOB_SIZE  = 50   # NAIP=500 — minimum water body size in pixels (50px = 5000m²)
MAX_HOLE_SIZE  = 100  # NAIP=1000 — holes smaller than this get filled
KEEP_TOP_N     = 3    # keep the 3 largest connected water bodies

# Sentinel band order for OmniWaterMask: R, G, B, NIR (1-based rasterio bands)
# From getSentinelCollection: 0=uBlue, 1=Blue, 2=Green, 3=Red, 4=NIR
# So rasterio bands (1-indexed): R=4, G=3, B=2, NIR=5
BAND_ORDER = [4, 3, 2, 5]

# Set to "cpu" or "cuda"
MOSAIC_DEVICE = "cuda"

# Buffer in meters if gpkgs are line features, None if already polygons
BUFFER_METERS = None

# Set to True to re-run masking even if output already exists
FORCE_RERUN = False

# =============================================================================
# SAFE PRINT
# =============================================================================

_original_print = builtins.print

def safe_print(*args, **kwargs):
    """Silently ignore stale file handle errors from NFS hiccups."""
    try:
        _original_print(*args, **kwargs, flush=True)
    except OSError:
        pass

builtins.print = safe_print

# =============================================================================
# SETUP
# =============================================================================

print(f"River:          {RIVER}")
print(f"GPKGs:          {GPKGS}")
print(f"GPKG dir:       {GPKG_DIR}")
print(f"Sentinel root:  {SENTINEL_ROOT}")
print()

if not GPKG_DIR.exists():
    print(f"ERROR: GPKG directory does not exist: {GPKG_DIR}")
    raise SystemExit(1)

if not SENTINEL_ROOT.exists():
    print(f"ERROR: Sentinel root does not exist: {SENTINEL_ROOT}")
    raise SystemExit(1)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def load_aoi(gpkg_path):
    """Load AOI from GeoPackage and return a single unified WGS84 geometry."""
    layers = fiona.listlayers(str(gpkg_path))
    gdf = gpd.read_file(gpkg_path, layer=layers[0])
    if BUFFER_METERS:
        gdf = gdf.to_crs("EPSG:3310")
        gdf["geometry"] = gdf.buffer(BUFFER_METERS)
    gdf = gdf.to_crs("EPSG:4326")
    return gdf.union_all()


def parse_year_from_image(path):
    """
    Extract start year from Sentinel image filename.
    e.g. sacramento_32_2018_01_01_2018_12_31_full_image.tif -> 2018
    """
    match = re.search(r'_(\d{4})_\d{2}_\d{2}_\d{4}_\d{2}_\d{2}_full_image', path.stem)
    return int(match.group(1)) if match else None


def verify_tile(fname):
    """Verify a tile is readable by sampling three locations."""
    try:
        with rasterio.open(fname) as src:
            h, w = src.height, src.width
            src.read(1, window=rasterio.windows.Window(0, 0, 256, 256))
            src.read(1, window=rasterio.windows.Window(w // 2, h // 2, 256, 256))
            src.read(1, window=rasterio.windows.Window(
                max(0, w - 256), max(0, h - 256), 256, 256))
        return True
    except Exception:
        return False


def clip_image_to_aoi(image_path, aoi):
    """
    Clip a Sentinel image to the AOI and save a temporary clipped version.
    Returns the path to the clipped file, or None if there is no overlap.
    """
    with rasterio.open(image_path) as src:
        tile_crs = src.crs
        aoi_gdf = gpd.GeoDataFrame(geometry=[aoi], crs="EPSG:4326")
        aoi_reprojected = aoi_gdf.to_crs(tile_crs).union_all()

        tile_bounds = box(*src.bounds)
        if not tile_bounds.intersects(aoi_reprojected):
            print(f"    No overlap with AOI, skipping")
            return None

        aoi_clipped = aoi_reprojected.intersection(tile_bounds)

        try:
            clipped, transform = rio_mask(
                src, [mapping(aoi_clipped)], crop=True, nodata=0, all_touched=True
            )
        except ValueError:
            return None

        clipped_path = image_path.parent / f"{image_path.stem}_clipped.tif"
        meta = src.meta.copy()
        meta.update({
            "height": clipped.shape[1],
            "width":  clipped.shape[2],
            "transform": transform,
        })
        with rasterio.open(clipped_path, "w", **meta) as dst:
            dst.write(clipped)

    return clipped_path


def clean_water_mask(mask,
                     closing_radius=CLOSING_RADIUS,
                     opening_radius=OPENING_RADIUS,
                     min_size=MIN_BLOB_SIZE,
                     max_hole_size=MAX_HOLE_SIZE,
                     keep_top_n=KEEP_TOP_N):
    """Spatially clean raw OmniWaterMask output for Sentinel-2 resolution."""
    cleaned = mask.copy()
    cleaned = closing(cleaned, footprint=disk(closing_radius))
    cleaned = remove_small_objects(cleaned, min_size=min_size)

    filled    = binary_fill_holes(cleaned)
    holes     = filled & ~cleaned
    big_holes = remove_small_objects(holes, min_size=max_hole_size)
    cleaned[holes & ~big_holes] = True

    cleaned = opening(cleaned, footprint=disk(opening_radius))

    labeled = label(cleaned, connectivity=2)
    if labeled.max() == 0:
        print("    WARNING: cleaning removed all water pixels, returning raw mask")
        return mask

    props = regionprops(labeled)
    top_components = sorted(props, key=lambda r: r.area, reverse=True)[:keep_top_n]
    top_labels = [r.label for r in top_components]

    return np.isin(labeled, top_labels)


def apply_cleaning_to_mask_file(mask_path):
    """Read an OmniWaterMask output GeoTIFF, clean it, write back to same file."""
    with rasterio.open(mask_path) as src:
        data = src.read(1).astype(bool)
        meta = src.meta.copy()

    cleaned = clean_water_mask(data)

    with rasterio.open(mask_path, "w", **meta) as dst:
        dst.write(cleaned.astype(np.uint8), 1)


# =============================================================================
# MAIN LOOP
# =============================================================================

gpkg_files = sorted(GPKG_DIR.glob("*.gpkg"))
print(f"Found {len(gpkg_files)} GeoPackages in {GPKG_DIR}\n")

for gpkg in gpkg_files:
    section_name = gpkg.stem
    print(f"{'='*50}")
    print(f"Processing: {section_name}")

    # ── Find corresponding Sentinel image folder ───────────────────────────
    section_dir = SENTINEL_ROOT / section_name
    image_dir   = section_dir / "image"
    omni_dir    = section_dir / "omni_mask"

    if not section_dir.exists():
        print(f"  Skipping — no Sentinel folder found at {section_dir}")
        continue

    if not image_dir.exists():
        print(f"  Skipping — no image folder found at {image_dir}")
        continue

    omni_dir.mkdir(parents=True, exist_ok=True)

    # ── Load AOI ───────────────────────────────────────────────────────────
    aoi = load_aoi(gpkg)

    # ── Find all Sentinel images for this section ──────────────────────────
    images_by_year = {}
    for image_path in sorted(image_dir.glob("*.tif")):
        year = parse_year_from_image(image_path)
        if year is not None:
            images_by_year[year] = image_path

    if not images_by_year:
        print(f"  Skipping — no Sentinel images found in {image_dir}")
        continue

    print(f"  Found images for years: {sorted(images_by_year.keys())}")

    # ── Process each year ──────────────────────────────────────────────────
    for year, image_path in sorted(images_by_year.items()):

        omni_out = omni_dir / f"{section_name}_{year}_omni_mask.tif"

        if omni_out.exists() and not FORCE_RERUN:
            print(f"  Skipping {year} — omni mask already exists")
            continue

        print(f"  Processing year {year}: {image_path.name}")

        # ── Clip image to AOI ──────────────────────────────────────────────
        clipped_path = clip_image_to_aoi(image_path, aoi)
        if clipped_path is None:
            print(f"  No overlap with AOI for {year}, skipping")
            continue

        # ── Run OmniWaterMask ──────────────────────────────────────────────
        try:
            result = make_water_mask(
                scene_paths=[clipped_path],
                band_order=BAND_ORDER,
                output_dir=omni_dir,
                mosaic_device=MOSAIC_DEVICE,
            )

            if result:
                for mask_path in result:
                    print(f"    Cleaning {mask_path.name}...")
                    apply_cleaning_to_mask_file(mask_path)
                    # ── Rename to our standard naming convention ───────────
                    mask_path.rename(omni_out)
                print(f"  Saved -> {omni_out.name}")
            else:
                print(f"  WARNING: OmniWaterMask returned no result for {year}")

        except Exception as e:
            print(f"  ERROR on {year}: {e}")

        finally:
            # ── Clean up clipped temp file ─────────────────────────────────
            if clipped_path and clipped_path.exists():
                clipped_path.unlink()

    print()

print("All done!")
