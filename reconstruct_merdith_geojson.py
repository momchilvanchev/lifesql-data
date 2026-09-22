from pathlib import Path
import pygplates

BASE = Path("data/raw/merdith-2021")

COASTLINES = BASE / "shapes_coastlines_Merdith_et_al.gpmlz"
ROTATIONS = BASE / "1000_0_rotfile_Merdith_et_al_optimised.rot"

AGE = 250

OUTPUT = BASE / f"coastlines-{AGE}Ma.geojson"

print(f"Input:     {COASTLINES}")
print(f"Rotations: {ROTATIONS}")
print(f"Time:      {AGE} Ma")
print(f"Output:    {OUTPUT}")

print("Reconstructing and exporting GeoJSON...")

pygplates.reconstruct(
    str(COASTLINES),
    pygplates.RotationModel(str(ROTATIONS)),
    str(OUTPUT),
    AGE,
)

print("Done.")
print(f"Saved: {OUTPUT}")
