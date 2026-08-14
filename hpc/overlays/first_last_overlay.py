import os
import re
from datetime import datetime
import rasterio
import numpy as np
import matplotlib.pyplot as plt
from PIL import Image
import matplotlib.colors as mcolors

# ── Settings ──────────────────────────────────────────────────────────────────
if os.path.isdir("/home/geomorph/slance"):
    BASE = "/home/geomorph/slance/california_rivers/gee_watermask"

yearly_root = os.path.join(BASE, "outputs/yearly_outputs/trin_yearly")
parent_folder_name = os.path.basename(yearly_root)
output_dir = os.path.join(BASE, "images", parent_folder_name)
os.makedirs(output_dir, exist_ok=True)

# Choose which subfolders to process
print(f"\nAvailable subfolders in {yearly_root}:")
all_subfolders = sorted([
    d for d in os.listdir(yearly_root)
    if os.path.isdir(os.path.join(yearly_root, d))
    and re.match(r'trin_\d+$', d)
])

for i, subfolder in enumerate(all_subfolders, 1):
    print(f"  {i}. {subfolder}")

selection = input("\nEnter subfolder number(s) to process (comma-separated, or 'all'): ").strip()

if selection.lower() == 'all':
    selected_subfolders = all_subfolders
else:
    indices = [int(x.strip()) - 1 for x in selection.split(',')]
    selected_subfolders = [all_subfolders[i] for i in indices if 0 <= i < len(all_subfolders)]

# ── Date extraction ───────────────────────────────────────────────────────────
def extract_date(filepath):
    fname = os.path.basename(filepath)
    match = re.search(r'(\d{4})_(\d{2})_(\d{2})_\d{4}_\d{2}_\d{2}', fname)
    if match:
        year, month, day = match.groups()
        return datetime(int(year), int(month), int(day))
    return datetime.min

# ── Process each selected subfolder ────────────────────────────────────────────
cmap = mcolors.ListedColormap(['#1a1a2e', '#f5c518'])

for subfolder in selected_subfolders:
    tif_dir = os.path.join(yearly_root, subfolder, "mask")

    if not os.path.isdir(tif_dir):
        print(f"⚠ Skipping {subfolder}: no 'mask' folder found")
        continue

    tif_files = sorted(
        [os.path.join(tif_dir, f) for f in os.listdir(tif_dir) if f.endswith('.tif')],
        key=extract_date
    )

    if len(tif_files) < 2:
        print(f"⚠ Skipping {subfolder}: fewer than 2 TIF files found")
        continue

    first_tif = tif_files[0]
    last_tif = tif_files[-1]

    print(f"\n── {subfolder} ──")
    print(f"   First: {os.path.basename(first_tif)}")
    print(f"   Last:  {os.path.basename(last_tif)}")

    # Read raster data
    with rasterio.open(first_tif) as src:
        first_data = src.read(1).astype(float)
        first_bounds = src.bounds

    with rasterio.open(last_tif) as src:
        last_data = src.read(1).astype(float)
        last_bounds = src.bounds

    # Mask the data
    first_data = np.ma.masked_where(first_data == 0, first_data)
    last_data = np.ma.masked_where(last_data == 0, last_data)

    # Create side-by-side figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(24, 8))
    fig.suptitle(f"{subfolder}", fontsize=20, fontweight='bold', color='white')
    fig.patch.set_facecolor('#1a1a2e')

    # First image
    ax1.set_facecolor('#1a1a2e')
    ax1.imshow(
        first_data.filled(0),
        cmap=cmap,
        vmin=0,
        vmax=1,
        extent=[first_bounds.left, first_bounds.right, first_bounds.bottom, first_bounds.top]
    )
    ax1.set_xlim(first_bounds.left, first_bounds.right)
    ax1.set_ylim(first_bounds.bottom, first_bounds.top)
    ax1.set_title("First Year", color='white', fontsize=14)
    ax1.set_xlabel("Longitude", color="white", fontsize=9)
    ax1.set_ylabel("Latitude", color="white", fontsize=9)
    ax1.tick_params(colors="white")
    for spine in ax1.spines.values():
        spine.set_edgecolor("white")

    # Last image
    ax2.set_facecolor('#1a1a2e')
    ax2.imshow(
        last_data.filled(0),
        cmap=cmap,
        vmin=0,
        vmax=1,
        extent=[last_bounds.left, last_bounds.right, last_bounds.bottom, last_bounds.top]
    )
    ax2.set_xlim(last_bounds.left, last_bounds.right)
    ax2.set_ylim(last_bounds.bottom, last_bounds.top)
    ax2.set_title("Last Year", color='white', fontsize=14)
    ax2.set_xlabel("Longitude", color="white", fontsize=9)
    ax2.set_ylabel("Latitude", color="white", fontsize=9)
    ax2.tick_params(colors="white")
    for spine in ax2.spines.values():
        spine.set_edgecolor("white")

    plt.tight_layout()

    output_path = os.path.join(output_dir, f"{subfolder}_yearly_first_last.png")
    plt.savefig(output_path, facecolor='#1a1a2e', dpi=100, bbox_inches='tight')
    plt.close(fig)

    print(f"   ✓ Saved → {output_path}")

print("\nAll done!")
