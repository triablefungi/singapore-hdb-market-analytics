from pathlib import Path

import pandas as pd


PROCESSED_DATA_DIR = Path("data/processed")

RESALE_PATH = PROCESSED_DATA_DIR / "hdb_resale_clean.csv"
RENTAL_PATH = PROCESSED_DATA_DIR / "hdb_rental_clean.csv"
OUTPUT_PATH = PROCESSED_DATA_DIR / "hdb_addresses_to_geocode.csv"


def load_address_counts(path: Path, count_name: str) -> pd.DataFrame:
    """Load, normalise and count addresses from one HDB dataset."""
    data = pd.read_csv(
        path,
        usecols=["address"],
        dtype={"address": "string"},
    )

    data["address"] = (
        data["address"]
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)
    )

    data = data.dropna(subset=["address"])
    data = data[data["address"] != ""]

    return (
        data.groupby("address", as_index=False)
        .size()
        .rename(columns={"size": count_name})
    )


def prepare_addresses() -> pd.DataFrame:
    """Create one unique address list across resale and rental records."""
    resale_counts = load_address_counts(
        RESALE_PATH,
        "resale_records",
    )
    rental_counts = load_address_counts(
        RENTAL_PATH,
        "rental_records",
    )

    addresses = resale_counts.merge(
        rental_counts,
        on="address",
        how="outer",
    )

    count_columns = ["resale_records", "rental_records"]

    addresses[count_columns] = (
        addresses[count_columns]
        .fillna(0)
        .astype("int64")
    )

    addresses["in_resale"] = addresses["resale_records"] > 0
    addresses["in_rental"] = addresses["rental_records"] > 0

    addresses = addresses[
        [
            "address",
            "in_resale",
            "in_rental",
            "resale_records",
            "rental_records",
        ]
    ].sort_values("address", ignore_index=True)

    if addresses["address"].duplicated().any():
        raise ValueError("Duplicate addresses remain after preparation.")

    if addresses["address"].isna().any():
        raise ValueError("Missing addresses remain after preparation.")

    return addresses


def main() -> None:
    addresses = prepare_addresses()

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    addresses.to_csv(
        OUTPUT_PATH,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )

    shared = (addresses["in_resale"] & addresses["in_rental"]).sum()

    print(f"Output file: {OUTPUT_PATH}")
    print(f"Unique addresses: {len(addresses):,}")
    print(f"Resale addresses: {addresses['in_resale'].sum():,}")
    print(f"Rental addresses: {addresses['in_rental'].sum():,}")
    print(f"Shared addresses: {shared:,}")
    print("\nFirst 10 rows:")
    print(addresses.head(10).to_string(index=False))


if __name__ == "__main__":
    main()