from __future__ import annotations

import math


PHI = (1.0 + math.sqrt(5.0)) / 2.0
EARTH_RADIUS_KM = 6371.0


def normalize(v):
    x, y, z = v
    length = math.sqrt(x * x + y * y + z * z)

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

    vertices = [normalize(v) for v in vertices]

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


def midpoint_index(a, b, vertices, cache):
    key = (min(a, b), max(a, b))

    if key in cache:
        return cache[key]

    va = vertices[a]
    vb = vertices[b]

    midpoint = normalize((
        (va[0] + vb[0]) / 2,
        (va[1] + vb[1]) / 2,
        (va[2] + vb[2]) / 2,
    ))

    index = len(vertices)

    vertices.append(midpoint)
    cache[key] = index

    return index


def subdivide(vertices, faces):
    cache = {}
    new_faces = []

    for a, b, c in faces:
        ab = midpoint_index(a, b, vertices, cache)
        bc = midpoint_index(b, c, vertices, cache)
        ca = midpoint_index(c, a, vertices, cache)

        new_faces.extend([
            (a, ab, ca),
            (b, bc, ab),
            (c, ca, bc),
            (ab, bc, ca),
        ])

    return new_faces


def angular_distance(a, b):
    dot = (
        a[0] * b[0] +
        a[1] * b[1] +
        a[2] * b[2]
    )

    dot = max(-1.0, min(1.0, dot))

    return math.acos(dot)


def edge_lengths(vertices, faces):
    edges = set()

    for a, b, c in faces:
        edges.add(tuple(sorted((a, b))))
        edges.add(tuple(sorted((b, c))))
        edges.add(tuple(sorted((c, a))))

    return [
        angular_distance(vertices[a], vertices[b])
        for a, b in edges
    ]


def main():
    vertices, faces = create_icosahedron()

    print()
    print("LifeSQL icosphere resolution analysis")
    print()
    print(
        f"{'LOD':>3} "
        f"{'Vertices':>15} "
        f"{'Triangles':>15} "
        f"{'Edges':>15} "
        f"{'Mean km':>12} "
        f"{'Min km':>12} "
        f"{'Max km':>12}"
    )
    print("-" * 90)

    for lod in range(13):
        lengths = edge_lengths(vertices, faces)

        mean_km = (
            sum(lengths) /
            len(lengths) *
            EARTH_RADIUS_KM
        )

        min_km = (
            min(lengths) *
            EARTH_RADIUS_KM
        )

        max_km = (
            max(lengths) *
            EARTH_RADIUS_KM
        )

        print(
            f"{lod:>3} "
            f"{len(vertices):>15,} "
            f"{len(faces):>15,} "
            f"{len(lengths):>15,} "
            f"{mean_km:>12.3f} "
            f"{min_km:>12.3f} "
            f"{max_km:>12.3f}"
        )

        faces = subdivide(vertices, faces)


if __name__ == "__main__":
    main()
