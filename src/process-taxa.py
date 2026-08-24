import csv
import sqlite3
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

INPUT = Path(
    "data/raw/catalogue-of-life-xr-2026-07-17/Taxon.tsv"
)

STAGING_DB = Path(
    "data/processed/taxa-staging.sqlite"
)

OUTPUT = Path(
    "data/processed/taxa.csv"
)

RANKS = {
    "domain": 1,
    "kingdom": 2,
    "subkingdom": 3,
    "infrakingdom": 4,
    "realm": 5,
    "phylum": 6,
    "subphylum": 7,
    "infraphylum": 8,
    "parvphylum": 9,
    "gigaclass": 10,
    "megaclass": 11,
    "superclass": 12,
    "class": 13,
    "subclass": 14,
    "infraclass": 15,
    "subterclass": 16,
    "order": 17,
    "suborder": 18,
    "infraorder": 19,
    "parvorder": 20,
    "nanorder": 21,
    "superorder": 22,
    "series zoology": 23,
    "section zoology": 24,
    "superfamily": 25,
    "epifamily": 26,
    "family": 27,
    "infrafamily": 28,
    "subfamily": 29,
    "tribe": 30,
    "infratribe": 31,
    "supertribe": 32,
    "subtribe": 33,
    "genus": 34,
    "subgenus": 35,
    "infrageneric name": 36,
    "section botany": 37,
    "subsection botany": 38,
    "species": 39,
    "species aggregate": 40,
    "subspecies": 41,
    "proles": 42,
    "variety": 43,
    "subvariety": 44,
    "form": 45,
    "subform": 46,
    "forma specialis": 47,
    "morph": 48,
    "natio": 49,
    "lusus": 50,
    "aberration": 51,
    "mutatio": 52,
    "infraspecific name": 53,
    "other": 54,
}


def clean_name(row):
    """
    Produce a clean scientific name without authorship.
    """

    rank = (row.get("dwc:taxonRank") or "").strip()

    genus = (row.get("dwc:genus") or "").strip()
    subgenus = (row.get("dwc:subgenus") or "").strip()
    species = (row.get("dwc:specificEpithet") or "").strip()
    infra = (row.get("dwc:infraspecificEpithet") or "").strip()

    scientific_name = (
        row.get("dwc:scientificName") or ""
    ).strip()

    # Species
    if rank == "species":
        if genus and species:
            if subgenus:
                return f"{genus} ({subgenus}) {species}"

            return f"{genus} {species}"

        # COL occasionally omits dwc:genus even though
        # dwc:scientificName contains a valid species name.
        if scientific_name:
            parts = scientific_name.split()

            if len(parts) >= 3 and parts[1].startswith("("):
                return f"{parts[0]} {parts[1]} {parts[2]}"

            if len(parts) >= 2:
                return f"{parts[0]} {parts[1]}"

        return None

    # Subspecies
    if rank == "subspecies":
        if genus and species and infra:
            if subgenus:
                return (
                    f"{genus} ({subgenus}) "
                    f"{species} {infra}"
                )

            return f"{genus} {species} {infra}"

        if scientific_name:
            parts = scientific_name.split()

            if len(parts) >= 4 and parts[1].startswith("("):
                return (
                    f"{parts[0]} {parts[1]} "
                    f"{parts[2]} {parts[3]}"
                )

            if len(parts) >= 3:
                return (
                    f"{parts[0]} "
                    f"{parts[1]} "
                    f"{parts[2]}"
                )

        return None

    # Ranks with dedicated Darwin Core fields.
    rank_fields = {
        "domain": "dwc:domain",
        "kingdom": "dwc:kingdom",
        "subkingdom": "dwc:subkingdom",
        "infrakingdom": "dwc:infrakingdom",
        "realm": "dwc:realm",
        "phylum": "dwc:phylum",
        "subphylum": "dwc:subphylum",
        "infraphylum": "dwc:infraphylum",
        "parvphylum": "dwc:parvphylum",
        "class": "dwc:class",
        "subclass": "dwc:subclass",
        "infraclass": "dwc:infraclass",
        "order": "dwc:order",
        "suborder": "dwc:suborder",
        "infraorder": "dwc:infraorder",
        "parvorder": "dwc:parvorder",
        "nanorder": "dwc:nanorder",
        "superorder": "dwc:superorder",
        "superfamily": "dwc:superfamily",
        "epifamily": "dwc:epifamily",
        "family": "dwc:family",
        "infrafamily": "dwc:infrafamily",
        "subfamily": "dwc:subfamily",
        "tribe": "dwc:tribe",
        "infratribe": "dwc:infratribe",
        "supertribe": "dwc:supertribe",
        "subtribe": "dwc:subtribe",
        "genus": "dwc:genus",
        "subgenus": "dwc:subgenus",
    }

    field = rank_fields.get(rank)

    if field:
        value = (row.get(field) or "").strip()

        if value:
            return value

    # Species-like ranks not covered above.
    if rank in {
        "species aggregate",
        "proles",
        "variety",
        "subvariety",
        "form",
        "subform",
        "forma specialis",
        "morph",
        "natio",
        "lusus",
        "aberration",
        "mutatio",
        "infraspecific name",
    }:
        if genus and species:
            if infra:
                return f"{genus} {species} {infra}"

            return f"{genus} {species}"

    # Remaining unusual ranks.
    #
    # Taxonomic names at these ranks are normally a single
    # nomenclatural word. The remaining text in scientificName
    # is authorship.
    if scientific_name:
        return scientific_name.split()[0]

    return None
     
def create_staging_database():
    if STAGING_DB.exists():
        STAGING_DB.unlink()

    STAGING_DB.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    connection = sqlite3.connect(
        STAGING_DB
    )

    connection.execute("""
        CREATE TABLE taxa (
            id INTEGER PRIMARY KEY,
            col_taxon_id TEXT NOT NULL UNIQUE,
            parent_col_taxon_id TEXT,
            name TEXT NOT NULL,
            rank INTEGER NOT NULL,
            status INTEGER NOT NULL
        )
    """)

    connection.execute("""
        CREATE INDEX idx_taxa_col_taxon_id
        ON taxa(col_taxon_id)
    """)

    connection.execute("""
        CREATE INDEX idx_taxa_parent_col_taxon_id
        ON taxa(parent_col_taxon_id)
    """)

    return connection


def main():
    print("Reading Catalogue of Life...")
    print(f"Input: {INPUT}")

    connection = create_staging_database()

    inserted = 0
    skipped_status = 0
    skipped_rank = 0
    skipped_name = 0

    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as infile:

        reader = csv.DictReader(
            infile,
            delimiter="\t",
        )

        for row in reader:
            status = (
                row.get("dwc:taxonomicStatus")
                or ""
            ).strip()

            if status not in {
                "accepted",
                "provisionally accepted",
            }:
                skipped_status += 1
                continue

            rank_name = (
                row.get("dwc:taxonRank")
                or ""
            ).strip()

            rank = RANKS.get(rank_name)

            if rank is None:
                skipped_rank += 1
                continue

            col_taxon_id = (
                row.get("dwc:taxonID")
                or ""
            ).strip()

            if not col_taxon_id:
                continue

            parent_col_taxon_id = (
                row.get(
                    "dwc:parentNameUsageID"
                )
                or ""
            ).strip() or None

            name = clean_name(row)

            if not name:
                skipped_name += 1
                continue

            status_id = (
                0
                if status == "accepted"
                else 1
            )

            inserted += 1

            connection.execute(
                """
                INSERT INTO taxa (
                    id,
                    col_taxon_id,
                    parent_col_taxon_id,
                    name,
                    rank,
                    status
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    inserted,
                    col_taxon_id,
                    parent_col_taxon_id,
                    name,
                    rank,
                    status_id,
                ),
            )

            if inserted % 100_000 == 0:
                connection.commit()

                print(
                    f"Processed {inserted:,} taxa..."
                )

    connection.commit()

    print()
    print(
        f"Accepted/provisionally accepted: "
        f"{inserted:,}"
    )
    print(
        f"Skipped other statuses: "
        f"{skipped_status:,}"
    )
    print(
        f"Skipped unknown ranks: "
        f"{skipped_rank:,}"
    )
    print(
        f"Skipped missing names: "
        f"{skipped_name:,}"
    )

    # Resolve COL parent IDs into our internal IDs.
    print()
    print("Resolving parent relationships...")

    connection.execute("""
        ALTER TABLE taxa
        ADD COLUMN parent_id INTEGER
    """)

    connection.execute("""
        UPDATE taxa
        SET parent_id = (
            SELECT parent.id
            FROM taxa AS parent
            WHERE parent.col_taxon_id =
                  taxa.parent_col_taxon_id
        )
        WHERE parent_col_taxon_id IS NOT NULL
    """)

    unresolved = connection.execute("""
        SELECT COUNT(*)
        FROM taxa
        WHERE parent_col_taxon_id IS NOT NULL
          AND parent_id IS NULL
    """).fetchone()[0]

    missing_parent = connection.execute("""
        SELECT COUNT(*)
        FROM taxa
        WHERE parent_col_taxon_id IS NULL
    """).fetchone()[0]

    print(
        f"Missing parent reference: "
        f"{missing_parent:,}"
    )

    print(
        f"Unresolved parent reference: "
        f"{unresolved:,}"
    )

    # Export the final clean dataset.
    print()
    print("Writing processed taxa.csv...")

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with OUTPUT.open(
        "w",
        encoding="utf-8",
        newline="",
    ) as outfile:

        writer = csv.writer(outfile)

        writer.writerow([
            "id",
            "col_taxon_id",
            "name",
            "rank",
            "parent_id",
            "status",
        ])

        cursor = connection.execute("""
            SELECT
                id,
                col_taxon_id,
                name,
                rank,
                parent_id,
                status
            FROM taxa
            ORDER BY id
        """)

        count = 0

        for row in cursor:
            writer.writerow(row)
            count += 1

    connection.close()

    print()
    print("Done.")
    print(f"Output: {OUTPUT}")
    print(f"Rows: {count:,}")
    print(f"Staging DB: {STAGING_DB}")


if __name__ == "__main__":
    main()
