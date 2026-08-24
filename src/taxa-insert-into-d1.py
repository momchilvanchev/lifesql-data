import csv
import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()

INPUT = Path("data/processed/taxa.csv")
BATCH_SIZE = 1_000

ACCOUNT_ID = os.environ["CLOUDFLARE_ACCOUNT_ID"]
DATABASE_ID = os.environ["CLOUDFLARE_D1_DATABASE_ID"]
API_TOKEN = os.environ["CLOUDFLARE_API_TOKEN"]

URL = (
    f"https://api.cloudflare.com/client/v4/accounts/"
    f"{ACCOUNT_ID}/d1/database/{DATABASE_ID}/query"
)


def read_first_batch():
    with INPUT.open(
        "r",
        encoding="utf-8",
        newline="",
    ) as infile:

        reader = csv.DictReader(infile)

        batch = []

        for row in reader:
            batch.append(row)

            if len(batch) == BATCH_SIZE:
                break

        return batch


def escape_sql(value):
    return value.replace("'", "''")


def insert_batch(batch):
    values = ", ".join(
        "("
        f"{int(row['id'])}, "
        f"'{escape_sql(row['col_taxon_id'])}', "
        f"'{escape_sql(row['name'])}', "
        f"{int(row['rank'])}, "
        f"{int(row['parent_id']) if row['parent_id'] else 'NULL'}, "
        f"{int(row['status'])}"
        ")"
        for row in batch
    )

    sql = f"""
INSERT OR IGNORE INTO taxa (
    id,
    col_taxon_id,
    name,
    rank,
    parent_id,
    status
)
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

    if not response.ok:
        print("HTTP status:", response.status_code)
        print("Response:")
        print(response.text)
        raise RuntimeError("Cloudflare D1 request failed")

    result = response.json()

    if not result.get("success"):
        raise RuntimeError(result)

    return result


def main():
    print(f"Reading: {INPUT}")
    print(f"Test batch size: {BATCH_SIZE:,}")
    print()

    batch = read_first_batch()

    print(f"Read {len(batch):,} rows.")
    print("Inserting batch into D1...")

    result = insert_batch(batch)

    changes = result["result"][0]["meta"]["changes"]

    print()
    print("Batch inserted successfully.")
    print(f"Rows sent: {len(batch):,}")
    print(f"Rows inserted: {changes:,}")


if __name__ == "__main__":
    main()