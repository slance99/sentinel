import subprocess
import glob
import os
import sys
from multiprocessing import Pool

sys.stdout.flush()
os.environ['PYTHONUNBUFFERED'] = '1'

# ── Base paths ────────────────────────────────────────────────────────────────
SCRIPT_BASE = "/home/geomorph/california_rivers/gee_watermask/hpc"
DATA_BASE = "/home/geomorph/california_rivers/naip/gpkgs/all"



# ── Get gpkg folder from command line argument ────────────────────────────────
# Run as: python3 run_all_yr.py <gpkg_folder>
# e.g.  : python3 run_all_yr.py rbc_small_gpkgs
if len(sys.argv) < 2:
    print("Usage: python3 run_all_yr.py <gpkg_folder>")
    print("Example: python3 run_all_yr.py rbc_small_gpkgs")
    sys.exit(1)

gpkg_folder = sys.argv[1]
gpkg_dir = DATA_BASE + "/" + gpkg_folder
gpkgs = sorted(glob.glob(gpkg_dir + "/*.gpkg"))

print(f"Looking for gpkgs in: {gpkg_dir}")
print(f"Found: {len(gpkgs)} gpkgs")

if not gpkgs:
    print("No gpkgs found — check the folder name and path.")
    sys.exit(1)

def run_river(poly):
    river = os.path.basename(poly).replace(".gpkg", "")
    print(f"Starting: {river}", flush=True)

    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "run_single_river_yr.sh")
    
    # Check script exists
    if not os.path.exists(script_path):
        print(f"ERROR: script not found at {script_path}", flush=True)
        return river, False

    result = subprocess.run(
        ["bash", script_path, poly],
        capture_output=False,
    )

    if result.returncode != 0:
        print(f"FAILED: {river}", flush=True)
        return river, False

    print(f"DONE: {river}", flush=True)
    return river, True

if __name__ == "__main__":
    # ── Number of rivers to process in parallel ───────────────────────────────
    # Keep this low to avoid GEE rate limit (429) errors.
    # Each river internally spawns its own GEE requests via multiprocess in
    # multi.py, so running too many rivers at once can overwhelm GEE quota.
    num_workers = 1

    print(f"Running {len(gpkgs)} rivers with {num_workers} workers...")

    # ── Run rivers in parallel ────────────────────────────────────────────────
    with Pool(processes=num_workers) as pool:
        results = pool.map(run_river, gpkgs)

    # ── Print summary ─────────────────────────────────────────────────────────
    print("\n=== Summary ===")
    for river, success in results:
        status = "✓" if success else "✗ FAILED"
        print(f"  {status}  {river}")
