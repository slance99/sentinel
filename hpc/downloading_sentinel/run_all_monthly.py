import subprocess
import glob
import os
import sys
from multiprocessing import Pool

# ── Base path ─────────────────────────────────────────────────────────────────
BASE = "/home/slance/california_rivers/gee_watermask"

# ── Hardcoded base gpkg path ──────────────────────────────────────────────────
GPKG_BASE = "/home/geomorph/california_rivers/naip/gpkgs/all"

# ── Get gpkg folder from command line argument ────────────────────────────────
if len(sys.argv) < 2:
    print("Usage: python3 run_all_monthly.py <gpkg_folder>")
    print("Example: python3 run_all_monthly.py red_bluff_colusa_gpkgs")
    sys.exit(1)

gpkg_folder = sys.argv[1]
gpkg_dir = GPKG_BASE + "/" + gpkg_folder
gpkgs = sorted(glob.glob(gpkg_dir + "/*.gpkg"))

print(f"Looking for gpkgs in: {gpkg_dir}", flush=True)
print(f"Found: {len(gpkgs)} gpkgs", flush=True)

if not gpkgs:
    print("No gpkgs found — check the folder name and path.")
    sys.exit(1)

def run_river(poly):
    """
    Runs run_single_river_monthly.sh for a single river gpkg.
    Returns the river name and whether it succeeded.
    """
    river = os.path.basename(poly).replace(".gpkg", "")
    print(f"Starting: {river}", flush=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))

    result = subprocess.run(
        ["bash", os.path.join(script_dir, "run_single_river_monthly.sh"), poly],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"FAILED: {river}", flush=True)
        return river, False

    print(f"DONE: {river}", flush=True)
    return river, True

if __name__ == "__main__":
    # ── Keep workers low to avoid GEE rate limits ─────────────────────────────
    # Monthly runs make many more GEE calls than yearly (96 per river vs 8)
    # so keep this at 1 or 2 to avoid 429 errors
    num_workers = 1

    print(f"Running {len(gpkgs)} rivers with {num_workers} workers...", flush=True)

    with Pool(processes=num_workers) as pool:
        results = pool.map(run_river, gpkgs)

    print("\n=== Summary ===")
    for river, success in results:
        status = "✓" if success else "✗ FAILED"
        print(f"  {status}  {river}")
