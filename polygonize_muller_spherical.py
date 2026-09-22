from pathlib import Path
from collections import defaultdict
import json
import math

import numpy as np
from scipy.spatial import SphericalVoronoi
from shapely.geometry import Polygon, MultiPolygon, mapping
from shapely.ops import unary_union


BASE = Path("data/raw/js-arias-gm-muller-2022-15af873")

PIXELS = BASE / "pixel-ids-360.tab"
LANDSCAPE = BASE / "muller-landscape-cao-paleomap-360-5.tab"

AGE = 250_000_000

# 2 = continental shelf
# 3 = lowlands
# 4 = highlands
# 5 = ice sheets
LAND_CLASSES = {2, 3, 4, 5}

OUTPUT = BASE / "250Ma-land-spherical.geojson"


# ------------------------------------------------------------
# Load pixel centres
# ------------------------------------------------------------

pixel_ids = []
latitudes = []
longitudes = []

with PIXELS.open() as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("pixel"):
            continue

        pixel, lat, lon = line.split()

        pixel_ids.append(int(pixel))
        latitudes.append(float(lat))
        longitudes.append(float(lon))

print(f"Loaded {len(pixel_ids):,} pixel centres")


# ------------------------------------------------------------
# Load land pixels for the requested age
# ------------------------------------------------------------

land_pixels = set()

with LANDSCAPE.open() as f:
    for line in f:
        line = line.strip()

        if not line or line.startswith("#") or line.startswith("equator"):
            continue

        equator, age, pixel, value = line.split()

        if int(equator) != 360:
            continue

        if int(age) != AGE:
            continue

        if int(value) in LAND_CLASSES:
            land_pixels.add(int(pixel))

print(
    f"Land pixels at {AGE / 1_000_000:g} Ma: "
    f"{len(land_pixels):,}"
)


# ------------------------------------------------------------
# Convert centres to 3D unit-sphere coordinates
# ------------------------------------------------------------

lat = np.radians(np.asarray(latitudes))
lon = np.radians(np.asarray(longitudes))

points = np.column_stack([
    np.cos(lat) * np.cos(lon),
    np.cos(lat) * np.sin(lon),
    np.sin(lat),
])


# ------------------------------------------------------------
# Spherical Voronoi tessellation
# ------------------------------------------------------------

print("Building spherical Voronoi tessellation...")

sv = SphericalVoronoi(points)

sv.sort_vertices_of_regions()

print(f"Generated {len(sv.regions):,} spherical cells")


# ------------------------------------------------------------
# Convert each spherical cell to lon/lat.
#
# Vertices are unwrapped around the pixel's centre so cells
# crossing ±180° do not become giant polygons.
# ------------------------------------------------------------

def xyz_to_lonlat(vertices):
    result = []

    for x, y, z in vertices:
        lon = math.degrees(math.atan2(y, x))
        lat = math.degrees(math.asin(max(-1.0, min(1.0, z))))

        result.append((lon, lat))

    return result


def unwrap_longitudes(coords, centre_lon):
    result = []

    for lon, lat in coords:
        while lon - centre_lon > 180:
            lon -= 360

        while lon - centre_lon < -180:
            lon += 360

        result.append((lon, lat))

    return result


# ------------------------------------------------------------
# Build only the land cells.
# ------------------------------------------------------------

cells = []

for index, region in enumerate(sv.regions):

    pixel = pixel_ids[index]

    if pixel not in land_pixels:
        continue

    vertices = sv.vertices[region]

    coords = xyz_to_lonlat(vertices)

    centre_lon = longitudes[index]

    coords = unwrap_longitudes(coords, centre_lon)

    if len(coords) < 3:
        continue

    polygon = Polygon(coords)

    if not polygon.is_valid:
        polygon = polygon.buffer(0)

    if not polygon.is_empty:
        cells.append(polygon)


print(f"Constructed {len(cells):,} land polygons")


# ------------------------------------------------------------
# Union adjacent cells.
# ------------------------------------------------------------

print("Unioning cells...")

land = unary_union(cells)

print(f"Result geometry: {land.geom_type}")

if isinstance(land, MultiPolygon):
    print(f"Result polygons: {len(land.geoms):,}")
elif land.geom_type == "Polygon":
    print("Result polygons: 1")


# ------------------------------------------------------------
# Export GeoJSON
# ------------------------------------------------------------

feature = {
    "type": "Feature",
    "properties": {
        "age_ma": AGE / 1_000_000,
        "layer": "land",
        "source": "Müller et al. 2022",
        "pixelation": 360,
    },
    "geometry": mapping(land),
}

output = {
    "type": "FeatureCollection",
    "features": [feature],
}

with OUTPUT.open("w") as f:
    json.dump(output, f)

print()
print(f"Saved: {OUTPUT}")
print(f"Size: {OUTPUT.stat().st_size / 1024:.1f} KB")
