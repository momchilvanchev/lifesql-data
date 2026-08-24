import csv
import sys
from pathlib import Path

csv.field_size_limit(sys.maxsize)

INPUT = Path("data/raw/catalogue-of-life-xr-2026-07-17/Taxon.tsv")
OUTPUT = Path("data/processed/accepted_species.csv")


def main():
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)

    count = 0

    with INPUT.open("r", encoding="utf-8", newline="") as infile, \
         OUTPUT.open("w", encoding="utf-8", newline="") as outfile:

        reader = csv.DictReader(infile, delimiter="\t")
        writer = csv.writer(outfile)

        writer.writerow(["scientific_name"])

        seen = set()

        for row in reader:
            status = (row.get("dwc:taxonomicStatus") or "").strip()
            rank = (row.get("dwc:taxonRank") or "").strip()

            if status != "accepted":
                continue

            if rank != "species":
                continue

            genus = (row.get("dwc:genus") or "").strip()
            subgenus = (row.get("dwc:infragenericEpithet") or "").strip()
            species = (row.get("dwc:specificEpithet") or "").strip()

            if not genus or not species:
                continue

            if subgenus:
                scientific_name = f"{genus} ({subgenus}) {species}"
            else:
                scientific_name = f"{genus} {species}"

            if " sp." in scientific_name.lower() or " spp." in scientific_name.lower():
                continue

            if scientific_name in seen:
                continue

            seen.add(scientific_name)
            writer.writerow([scientific_name])
            count += 1

            if count % 100_000 == 0:
                print(f"Extracted {count:,} species...")

    print(f"Done. Extracted {count:,} accepted species.")
    print(f"Output: {OUTPUT}")


if __name__ == "__main__":
    main()