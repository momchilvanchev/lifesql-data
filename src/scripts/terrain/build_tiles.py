from __future__ import annotations

import json
import math
import struct
from pathlib import Path

from osgeo import gdal


SOURCE = Path("data/raw/GEBCO_2026.tif")
OUTPUT = Path("data/terrain/gebco-2026")

MAX_LOD = 8
EARTH_RADIUS_METRES = 6_371_000.0

# Stored elevation precision.
# GEBCO is metre-scale, so int16 is sufficient for Earth elevation.
ELEVATION_NO_DATA = -32768


PHI = (1.0 + math.sqrt(5.0)) / 2.0


def normalize(v):
    x, y, z = v

    length = math.sqrt(
        x * x +
        y * y +
        z * z
    )

    return (
        x / length,
        y / length,
        z / length,
    )


def create_icosahedron():
    vertices = [
        (-1, PHI, 0),
        (1, PHI, 0),
        (-1, -PHI, 0),
        (1, -PHI, 0),

        (0, -1, PHI),
        (0, 1, PHI),
        (0, -1, -PHI),
        (0, 1, -PHI),

        (PHI, 0, -1),
        (PHI, 0, 1),
        (-PHI, 0, -1),
        (-PHI, 0, 1),
    ]

    vertices = [
        normalize(v)
        for v in vertices
    ]

    faces = [
        (0, 11, 5),
        (0, 5, 1),
        (0, 1, 7),
        (0, 7, 10),
        (0, 10, 11),

        (1, 5, 9),
        (5, 11, 4),
        (11, 10, 2),
        (10, 7, 6),
        (7, 1, 8),

        (3, 9, 4),
        (3, 4, 2),
        (3, 2, 6),
        (3, 6, 8),
        (3, 8, 9),

        (4, 9, 5),
        (2, 4, 11),
        (6, 2, 10),
        (8, 6, 7),
        (9, 8, 1),
    ]

    return vertices, faces


def midpoint(a, b):
    return normalize((
        (a[0] + b[0]) * 0.5,
        (a[1] + b[1]) * 0.5,
        (a[2] + b[2]) * 0.5,
    ))


def subdivide_face(vertices, faces):
    """
    Subdivide one triangular mesh globally.

    Vertices are deduplicated by edge, so the resulting
    hierarchy has exactly the normal icosphere topology.
    """

    cache = {}
    new_faces = []

    def midpoint_index(a, b):
        key = (
            min(a, b),
            max(a, b),
        )

        if key in cache:
            return cache[key]

        value = midpoint(
            vertices[a],
            vertices[b],
        )

        index = len(vertices)

        vertices.append(value)
        cache[key] = index

        return index

    for a, b, c in faces:
        ab = midpoint_index(a, b)
        bc = midpoint_index(b, c)
        ca = midpoint_index(c, a)

        new_faces.extend([
            (a, ab, ca),
            (b, bc, ab),
            (c, ca, bc),
            (ab, bc, ca),
        ])

    return new_faces


def longitude_latitude(vertex):
    x, y, z = vertex

    latitude = math.degrees(
        math.asin(
            max(-1.0, min(1.0, y))
        )
    )

    longitude = -math.degrees(
        math.atan2(z, x)
    ) - 90.0

    while longitude < -180.0:
        longitude += 360.0

    while longitude > 180.0:
        longitude -= 360.0

    return longitude, latitude


class ElevationSampler:
    def __init__(self, path):
        self.dataset = gdal.Open(
            str(path),
            gdal.GA_ReadOnly,
        )

        if self.dataset is None:
            raise RuntimeError(
                f"Could not open {path}"
            )

        self.band = self.dataset.GetRasterBand(1)

        self.width = self.dataset.RasterXSize
        self.height = self.dataset.RasterYSize

        transform = self.dataset.GetGeoTransform()

        self.origin_x = transform[0]
        self.pixel_width = transform[1]
        self.origin_y = transform[3]
        self.pixel_height = transform[5]

        self.nodata = self.band.GetNoDataValue()

    def sample(self, longitude, latitude):
        """
        Bilinear sample from GEBCO.

        GEBCO:
            origin = (-180, +90)
            pixel width = +0.004166...
            pixel height = -0.004166...
        """

        px = (
            longitude -
            self.origin_x
        ) / self.pixel_width

        py = (
            latitude -
            self.origin_y
        ) / self.pixel_height

        x0 = math.floor(px)
        y0 = math.floor(py)

        fx = px - x0
        fy = py - y0

        x0 = max(
            0,
            min(
                self.width - 1,
                x0,
            ),
        )

        y0 = max(
            0,
            min(
                self.height - 1,
                y0,
            ),
        )

        x1 = min(
            self.width - 1,
            x0 + 1,
        )

        y1 = min(
            self.height - 1,
            y0 + 1,
        )

        values = self.band.ReadAsArray(
            x0,
            y0,
            2 if x1 != x0 else 1,
            2 if y1 != y0 else 1,
        )

        def value(x, y):
            local_x = x - x0
            local_y = y - y0

            result = float(
                values[
                    local_y,
                    local_x,
                ]
            )

            if (
                not math.isfinite(result)
                or (
                    self.nodata is not None
                    and result == self.nodata
                )
            ):
                return 0.0

            return result

        v00 = value(x0, y0)
        v10 = value(x1, y0)
        v01 = value(x0, y1)
        v11 = value(x1, y1)

        top = (
            v00 +
            (v10 - v00) * fx
        )

        bottom = (
            v01 +
            (v11 - v01) * fx
        )

        return (
            top +
            (bottom - top) * fy
        )


def write_tile(
    path,
    lod,
    face_id,
    vertices,
    faces,
    elevations,
):
    path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    # Binary format v1:
    #
    # Header:
    #   magic       4 bytes  "LSQL"
    #   version     uint8
    #   lod         uint8
    #   face        uint8
    #   reserved    uint8
    #   vertices    uint32
    #   triangles   uint32
    #
    # Then:
    #   vertex positions: float32 × 3
    #   elevations:       int16
    #   indices:          uint32 × 3

    with path.open("wb") as f:
        f.write(b"LSQL")
        f.write(struct.pack(
            "<BBBBII",
            1,
            lod,
            face_id,
            0,
            len(vertices),
            len(faces),
        ))

        for vertex in vertices:
            f.write(struct.pack(
                "<fff",
                vertex[0],
                vertex[1],
                vertex[2],
            ))

        for elevation in elevations:
            value = int(
                max(
                    -32767,
                    min(
                        32767,
                        round(elevation),
                    ),
                )
            )

            f.write(
                struct.pack(
                    "<h",
                    value,
                )
            )

        for a, b, c in faces:
            f.write(
                struct.pack(
                    "<III",
                    a,
                    b,
                    c,
                )
            )


def build():
    if not SOURCE.exists():
        raise RuntimeError(
            f"Missing source raster: {SOURCE}"
        )

    OUTPUT.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("LifeSQL terrain tile generator")
    print()
    print(f"Source: {SOURCE}")
    print(f"Output: {OUTPUT}")
    print(f"Maximum LOD: {MAX_LOD}")
    print()

    sampler = ElevationSampler(SOURCE)

    vertices, faces = create_icosahedron()

    all_lods = [
        (
            list(vertices),
            list(faces),
        )
    ]

    for lod in range(MAX_LOD):
        print(
            f"Generating topology for LOD {lod + 1}..."
        )

        next_vertices = list(
            all_lods[-1][0]
        )

        next_faces = subdivide_face(
            next_vertices,
            all_lods[-1][1],
        )

        all_lods.append(
            (
                next_vertices,
                next_faces,
            )
        )

    manifest = {
        "dataset": "GEBCO 2026",
        "version": 1,
        "maxLod": MAX_LOD,
        "earthRadiusMetres": EARTH_RADIUS_METRES,
        "rootFaces": 20,
        "source": {
            "width": sampler.width,
            "height": sampler.height,
            "pixelSizeDegrees": abs(
                sampler.pixel_width
            ),
        },
        "format": {
            "name": "lifesql-terrain",
            "version": 1,
            "elevationType": "int16-metres",
            "positionType": "float32",
            "indexType": "uint32",
        },
    }

    with (
        OUTPUT /
        "manifest.json"
    ).open(
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            manifest,
            f,
            indent=2,
        )

    # For the first prototype we write each global LOD
    # as one complete dataset.
    #
    # This is intentionally NOT the final streaming
    # format. It lets us validate the sampling and
    # binary representation before introducing
    # hierarchical tile boundaries.

    for lod, (
        lod_vertices,
        lod_faces,
    ) in enumerate(all_lods):

        print()
        print(
            f"Sampling LOD {lod}: "
            f"{len(lod_vertices):,} vertices"
        )

        elevations = []

        for index, vertex in enumerate(
            lod_vertices
        ):
            longitude, latitude = (
                longitude_latitude(vertex)
            )

            elevation = sampler.sample(
                longitude,
                latitude,
            )

            elevations.append(
                elevation
            )

            if (
                index % 100 == 0
                or index == len(lod_vertices) - 1
            ):
                print(
                    f"\r  {index + 1:,} / "
                    f"{len(lod_vertices):,}",
                    end="",
                    flush=True,
                )

        print()

        path = (
            OUTPUT /
            f"l{lod}.bin"
        )

        write_tile(
            path,
            lod,
            255,
            lod_vertices,
            lod_faces,
            elevations,
        )

        print(
            f"  wrote {path} "
            f"({path.stat().st_size:,} bytes)"
        )

    print()
    print("Done.")
    print()
    print(f"Dataset: {OUTPUT}")
    print()


if __name__ == "__main__":
    build()
