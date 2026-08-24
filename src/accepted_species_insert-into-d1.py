import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

INPUT = Path("data/processed/accepted_species.csv")
BATCH_SIZE = 1_000

ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
DATABASE_ID = os.environ["CLOUDFLARE_D1_DATABASE_ID"]
API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]

URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
)


def read_batches():
    with INPUT.open("r", encoding="utf-8", newline="") as infile:
        reader = csv.DictReader(infile)

        batch = []

        for row in reader:
            name = row["scientific_name"].strip()

            if not name:
                continue

            batch.append(name)

            if len(batch) == BATCH_SIZE:
                yield batch
                batch = []

        if batch:
            yield batch

def escape_sql(value):
    return value.replace("'", "''")


def insert_batch(batch):
    values = ", ".join(
        f"('{escape_sql(name)}')"
        for name in batch
    )

    sql = f"""
INSERT OR IGNORE INTO organisms (scientific_name)
VALUES {values};
"""

    response = requests.post(
        URL,
        headers={
            "Authorization": f"Bearer {API_TOKEN}",
            "Content-Type": "application/json",
        },
        json={
            "sql": sql,
        },
    )

    response.raise_for_status()

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(result)

    return result


def main():
    total = 0
    batches = 0

    for batch in read_batches():
        batches += 1

        result = insert_batch(batch)

        changes = result["result"][0]["meta"]["changes"]
        total += changes

        print(
            f"Batch {batches:,}: "
            f"{len(batch):,} rows sent, "
            f"{changes:,} inserted, "
            f"{total:,} inserted total"
        )

    print(f"\nDone. Inserted {total:,} new organisms.")

if __name__ == "__main__":
    main()