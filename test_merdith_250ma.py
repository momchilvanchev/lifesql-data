from pathlib import Path
import pygplates

BASE = Path("data/raw/merdith-2021")

COASTLINES = BASE / "shapes_coastlines_Merdith_et_al.gpmlz"
ROTATIONS = BASE / "1000_0_rotfile_Merdith_et_al_optimised.rot"

AGE = 250

print("Loading coastline features...")
features = pygplates.FeatureCollection(str(COASTLINES))

print("Loading rotation model...")
rotation_model = pygplates.RotationModel(str(ROTATIONS))

print(f"Features: {len(features):,}")
print(f"Reconstructing at {AGE} Ma...")

reconstructed = []

pygplates.reconstruct(
    features,
    rotation_model,
    reconstructed,
    AGE,
)

print(f"Reconstructed geometries: {len(reconstructed):,}")

output = BASE / f"reconstructed-{AGE}Ma.gpmlz"

out_features = []

for reconstructed_feature in reconstructed:
    feature = reconstructed_feature.get_feature()
    geometry = reconstructed_feature.get_reconstructed_geometry()

    if geometry is None:
        continue

    feature.set_geometry(geometry)
    out_features.append(feature)

pygplates.FeatureCollection(out_features).write(str(output))

print(f"Saved:")
print(output)
