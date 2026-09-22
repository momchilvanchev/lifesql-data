from pathlib import Path
import json

from shapely.geometry import Polygon, mapping
from shapely.ops import unary_union

BASE = Path("data/raw/js-arias-gm-muller-2022-15af873")

PIXELS = BASE / "pixel-ids-360.tab"
LANDSCAPE = BASE / "muller-landscape-cao-paleomap-360-5.tab"

AGE = 250_000_000

LAND_CLASSES = {2, 3, 4, 5}

OUTPUT = BASE / "250Ma-land.geojson"


# ------------------------------------------------------------
# Load pixel centers
# ------------------------------------------------------------

pixels = {}

with PIXELS.open() as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("pixel"):
            continue

        pixel, lat, lon = line.split()

        pixels[int(pixel)] = (float(lat), float(lon))

print(f"Loaded {len(pixels):,} pixels")


# ------------------------------------------------------------
# Find land pixels at requested age
# ------------------------------------------------------------

land_pixels = set()

with LANDSCAPE.open() as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("equator"):
            continue

        pixelation, age, pixel, value = line.split()

        if int(pixelation) != 360:
            continue

        if int(age) != AGE:
            continue

        if int(value) in LAND_CLASSES:
            land_pixels.add(int(pixel))

print(f"Land pixels at {AGE / 1_000_000:g} Ma: {len(land_pixels):,}")


# ------------------------------------------------------------
# The 360 grid is:
#
#   1° latitude spacing
#   variable longitude spacing depending on latitude
#
# The pixel coordinates themselves define the centers.
# We derive the nearest neighboring longitude/latitude spacing.
# ------------------------------------------------------------

# Latitude rows
rows = {}

for pixel, (lat, lon) in pixels.items():
    rows.setdefault(lat, []).append((lon, pixel))

latitudes = sorted(rows)

lat_step = min(
    b - a
    for a, b in zip(latitudes, latitudes[1:])
    if b > a
)

print(f"Latitude spacing: {lat_step}°")


# ------------------------------------------------------------
# Create cells.
#
# Longitude spacing varies by latitude in the equal-area
# pixelization, so determine it separately for every row.
# ------------------------------------------------------------

cells = []

for lat in latitudes:

    row = sorted(rows[lat])

    if len(row) < 2:
        continue

    # Most common longitude spacing in this row.
    spacings = [
        b[0] - a[0]
        for a, b in zip(row, row[1:])
        if b[0] > a[0]
    ]

    if not spacings:
        continue

    lon_step = min(spacings)

    lat0 = max(-90.0, lat - lat_step / 2)
    lat1 = min(90.0, lat + lat_step / 2)

    for i, (lon, pixel) in enumerate(row):

        if pixel not in land_pixels:
            continue

        lon0 = lon - lon_step / 2
        lon1 = lon + lon_step / 2

        cell = Polygon([
            (lon0, lat0),
            (lon1, lat0),
            (lon1, lat1),
            (lon0, lat1),
            (lon0, lat0),
        ])

        cells.append(cell)

print(f"Created {len(cells):,} land cells")


# ------------------------------------------------------------
# Union adjacent cells
# ------------------------------------------------------------

print("Unioning...")

land = unary_union(cells)

print(f"Geometry type: {land.geom_type}")

if hasattr(land, "geoms"):
    print(f"Polygon count: {len(land.geoms):,}")
else:
    print("Polygon count: 1")


# ------------------------------------------------------------
# Export
# ------------------------------------------------------------

feature = {
    "type": "Feature",
    "properties": {
        "age_ma": AGE / 1_000_000,
        "layer": "land",
        "source": "Muller et al. 2022",
    },
    "geometry": mapping(land),
}

geojson = {
    "type": "FeatureCollection",
    "features": [feature],
}

with OUTPUT.open("w") as f:
    json.dump(geojson, f)

print(f"Saved: {OUTPUT}")
print(f"Size: {OUTPUT.stat().st_size / 1024:.1f} KB")
