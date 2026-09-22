from pathlib import Path
import csv
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon
from matplotlib.collections import PatchCollection

BASE = Path("data/raw/js-arias-gm-muller-2022-15af873")
PIXELS_FILE = BASE / "pixel-ids-360.tab"
LANDSCAPE_FILE = BASE / "muller-landscape-cao-paleomap-360-5.tab"
OUT_DIR = BASE / "previews"

OUT_DIR.mkdir(exist_ok=True)

# Landscape classes
COLORS = {
    0: "#364b9a",  # deep ocean
    1: "#4a7bb7",  # oceanic plateaus
    2: "#98cae1",  # continental shelf
    3: "#feda8b",  # lowlands
    4: "#f67e4b",  # highlands
    5: "#e7e7e7",  # ice sheets
}

# ----------------------------------------------------------------------
# Read pixel centers
# ----------------------------------------------------------------------

pixels = {}

with open(PIXELS_FILE, newline="") as f:
    reader = csv.DictReader(
        (line for line in f if not line.startswith("#")),
        delimiter="\t",
    )

    for row in reader:
        pixels[int(row["pixel"])] = (
            float(row["lat"]),
            float(row["lon"]),
        )

print(f"Loaded {len(pixels):,} pixels")

# Group pixels by latitude
rows = {}

for pixel_id, (lat, lon) in pixels.items():
    rows.setdefault(lat, []).append((lon, pixel_id))

for lat in rows:
    rows[lat].sort()

latitudes = sorted(rows)

# ----------------------------------------------------------------------
# Calculate latitude boundaries
# ----------------------------------------------------------------------

lat_bounds = {}

for i, lat in enumerate(latitudes):
    if i == 0:
        south = -90
    else:
        south = (latitudes[i - 1] + lat) / 2

    if i == len(latitudes) - 1:
        north = 90
    else:
        north = (lat + latitudes[i + 1]) / 2

    lat_bounds[lat] = (south, north)

# ----------------------------------------------------------------------
# Calculate longitude boundaries for each row
# ----------------------------------------------------------------------

pixel_polygons = {}

for lat in latitudes:
    row = rows[lat]

    for i, (lon, pixel_id) in enumerate(row):
        prev_lon = row[i - 1][0] if i > 0 else row[-1][0] - 360
        next_lon = row[i + 1][0] if i < len(row) - 1 else row[0][0] + 360

        west = (prev_lon + lon) / 2
        east = (lon + next_lon) / 2

        # Normalize into [-180, 180]
        south, north = lat_bounds[lat]

        pixel_polygons[pixel_id] = [
            (west, south),
            (east, south),
            (east, north),
            (west, north),
        ]

# ----------------------------------------------------------------------
# Read landscape values
# ----------------------------------------------------------------------

snapshots = {}

with open(LANDSCAPE_FILE, newline="") as f:
    for line in f:
        if line.startswith("#") or line.startswith("equator"):
            continue

        parts = line.strip().split()

        if len(parts) < 4:
            continue

        equator = int(parts[0])
        age = int(parts[1])
        pixel_id = int(parts[2])
        value = int(parts[3])

        if equator != 360:
            continue

        snapshots.setdefault(age, {})[pixel_id] = value

print(f"Loaded {len(snapshots):,} snapshots")

# ----------------------------------------------------------------------
# Render every 5 Ma
# ----------------------------------------------------------------------

for age in sorted(snapshots):
    print(f"Rendering {age / 1_000_000:g} Ma...")

    values = snapshots[age]

    patches = []
    colors = []

    for pixel_id, value in values.items():
        polygon = pixel_polygons.get(pixel_id)

        if polygon is None:
            continue

        patches.append(Polygon(polygon, closed=True))
        colors.append(COLORS.get(value, "#000000"))

    fig, ax = plt.subplots(figsize=(16, 8), dpi=150)

    collection = PatchCollection(
        patches,
        facecolor=colors,
        edgecolor="none",
        linewidth=0,
    )

    ax.add_collection(collection)

    ax.set_xlim(-180, 180)
    ax.set_ylim(-90, 90)
    ax.set_aspect("equal")

    ax.set_title(f"{age / 1_000_000:g} Ma", fontsize=18)

    ax.axis("off")

    output = OUT_DIR / f"{age // 1_000_000:03d}Ma.png"

    plt.savefig(
        output,
        bbox_inches="tight",
        pad_inches=0,
        facecolor="#364b9a",
    )

    plt.close(fig)

print(f"\nDone. PNGs saved to:")
print(OUT_DIR)
