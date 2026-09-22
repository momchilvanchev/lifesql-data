from pathlib import Path
import pygplates
import matplotlib.pyplot as plt

BASE = Path("data/raw/merdith-2021")
INPUT = BASE / "reconstructed-250Ma.gpmlz"
OUTPUT = BASE / "reconstructed-250Ma.png"

features = pygplates.FeatureCollection(str(INPUT))

fig, ax = plt.subplots(figsize=(16, 8))

rendered = 0

for feature in features:
    geometry = feature.get_geometry()

    if geometry is None:
        continue

    # PolygonOnSphere
    try:
        rings = geometry.get_exterior_boundary_points()
    except AttributeError:
        continue

    if not rings:
        continue

    points = []

    for point in rings:
        lat, lon = point.to_lat_lon()
        points.append((lon, lat))

    if len(points) < 3:
        continue

    xs = [p[0] for p in points]
    ys = [p[1] for p in points]

    ax.fill(
        xs,
        ys,
        facecolor="black",
        edgecolor="red",
        linewidth=0.2,
    )

    rendered += 1

ax.set_xlim(-180, 180)
ax.set_ylim(-90, 90)
ax.set_aspect("equal")

ax.set_xlabel("Longitude")
ax.set_ylabel("Latitude")
ax.set_title("Merdith 2021 — reconstructed 250 Ma")

plt.tight_layout()
plt.savefig(OUTPUT, dpi=200, facecolor="white")
plt.close()

print(f"Features: {len(features):,}")
print(f"Rendered: {rendered:,}")
print(f"Saved: {OUTPUT}")
