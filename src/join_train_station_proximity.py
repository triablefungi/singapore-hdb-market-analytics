import argparse
from pathlib import Path

import pandas as pd


DEFAULT_PROXIMITY_PATH = Path(
    "data/processed/hdb_address_train_proximity.csv"
)

DEFAULT_RENTAL_INPUT_PATH = Path(
    "data/processed/hdb_rental_clean.csv"
)

DEFAULT_RESALE_INPUT_PATH = Path(
    "data/processed/hdb_resale_clean.csv"
)

DEFAULT_RENTAL_OUTPUT_PATH = Path(
    "data/processed/hdb_rental_with_train_proximity.csv"
)

DEFAULT_RESALE_OUTPUT_PATH = Path(
    "data/processed/hdb_resale_with_train_proximity.csv"
)

PROXIMITY_COLUMNS = [
    "nearest_train_station",
    "nearest_train_type",
    "nearest_train_distance_km",
    "nearest_mrt_station",
    "nearest_mrt_distance_km",
    "nearest_lrt_station",
    "nearest_lrt_distance_km",
]


def enrich_transactions(
    transactions,
    proximity,
    dataset_name,
    expected_unmatched_rows,
    expected_unmatched_addresses,
):
    conflicting_columns = (
        set(PROXIMITY_COLUMNS)
        & set(transactions.columns)
    )

    if conflicting_columns:
        raise ValueError(
            f"{dataset_name} already contains proximity "
            f"columns: {sorted(conflicting_columns)}"
        )

    enriched = transactions.merge(
        proximity,
        on="address",
        how="left",
        validate="many_to_one",
        indicator="_proximity_merge_status",
    )

    enriched["train_proximity_match_status"] = (
        enriched["_proximity_merge_status"]
        .map(
            {
                "both": "matched",
                "left_only": "unmatched",
                "right_only": "unused",
            }
        )
        .astype("string")
    )

    enriched = enriched.drop(
        columns="_proximity_merge_status"
    )

    matched = enriched[
        enriched["train_proximity_match_status"]
        == "matched"
    ]

    unmatched = enriched[
        enriched["train_proximity_match_status"]
        == "unmatched"
    ]

    checks = {
        "Transaction row count preserved": (
            len(enriched) == len(transactions)
        ),
        "Source row IDs remain unique": (
            not enriched["source_row_id"]
            .duplicated()
            .any()
        ),
        "All matched rows have proximity fields": (
            matched[PROXIMITY_COLUMNS]
            .notna()
            .all()
            .all()
        ),
        "All unmatched rows have null proximity fields": (
            unmatched[PROXIMITY_COLUMNS]
            .isna()
            .all()
            .all()
        ),
        "Expected unmatched row count": (
            len(unmatched) == expected_unmatched_rows
        ),
        "Expected unmatched address count": (
            unmatched["address"].nunique()
            == expected_unmatched_addresses
        ),
    }

    print(f"\n{'=' * 70}")
    print(f"{dataset_name} enrichment")
    print(f"Rows before join: {len(transactions):,}")
    print(f"Rows after join:  {len(enriched):,}")
    print(f"Matched rows:     {len(matched):,}")
    print(f"Unmatched rows:   {len(unmatched):,}")
    print(
        "Unmatched unique addresses: "
        f"{unmatched['address'].nunique():,}"
    )

    print("\nValidation checks:")

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        raise ValueError(
            f"{dataset_name} enrichment validation failed."
        )

    if not unmatched.empty:
        print("\nUnmatched addresses:")
        print(
            unmatched[
                ["address"]
            ]
            .value_counts()
            .rename("transaction_rows")
            .reset_index()
            .to_string(index=False)
        )

    return enriched


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Join train-station proximity features to "
            "the cleaned HDB rental and resale datasets."
        )
    )

    parser.add_argument(
        "--proximity",
        type=Path,
        default=DEFAULT_PROXIMITY_PATH,
    )

    parser.add_argument(
        "--rental-input",
        type=Path,
        default=DEFAULT_RENTAL_INPUT_PATH,
    )

    parser.add_argument(
        "--resale-input",
        type=Path,
        default=DEFAULT_RESALE_INPUT_PATH,
    )

    parser.add_argument(
        "--rental-output",
        type=Path,
        default=DEFAULT_RENTAL_OUTPUT_PATH,
    )

    parser.add_argument(
        "--resale-output",
        type=Path,
        default=DEFAULT_RESALE_OUTPUT_PATH,
    )

    args = parser.parse_args()

    proximity = pd.read_csv(
        args.proximity,
        dtype={"address": "string"},
    )

    if proximity["address"].duplicated().any():
        raise ValueError(
            "The proximity lookup contains duplicate addresses."
        )

    rental = pd.read_csv(
        args.rental_input,
        dtype={
            "address": "string",
            "source_row_id": "string",
        },
    )

    resale = pd.read_csv(
        args.resale_input,
        dtype={
            "address": "string",
            "source_row_id": "string",
        },
    )

    rental_enriched = enrich_transactions(
        transactions=rental,
        proximity=proximity,
        dataset_name="Rental",
        expected_unmatched_rows=37,
        expected_unmatched_addresses=9,
    )

    resale_enriched = enrich_transactions(
        transactions=resale,
        proximity=proximity,
        dataset_name="Resale",
        expected_unmatched_rows=0,
        expected_unmatched_addresses=0,
    )

    args.rental_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.resale_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rental_enriched.to_csv(
        args.rental_output,
        index=False,
        float_format="%.6f",
    )

    resale_enriched.to_csv(
        args.resale_output,
        index=False,
        float_format="%.6f",
    )

    print("\nSaved enriched rental dataset to:")
    print(args.rental_output)

    print("\nSaved enriched resale dataset to:")
    print(args.resale_output)


if __name__ == "__main__":
    main()