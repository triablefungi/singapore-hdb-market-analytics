import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_RENTAL_INPUT_PATH = Path(
    "data/processed/hdb_rental_with_train_proximity.csv"
)

DEFAULT_RESALE_INPUT_PATH = Path(
    "data/processed/hdb_resale_with_train_proximity.csv"
)

DEFAULT_RENTAL_OUTPUT_PATH = Path(
    "data/processed/hdb_rental_analysis_ready.csv"
)

DEFAULT_RESALE_OUTPUT_PATH = Path(
    "data/processed/hdb_resale_analysis_ready.csv"
)

DISTANCE_BINS = [
    -np.inf,
    0.4,
    0.8,
    1.2,
    np.inf,
]

DISTANCE_LABELS = [
    "0-400m",
    "400-800m",
    "800m-1.2km",
    "over-1.2km",
]

COMMON_FEATURE_COLUMNS = [
    "calendar_year",
    "calendar_month",
    "calendar_quarter",
    "train_distance_band",
    "train_within_800m",
]

RESALE_FEATURE_COLUMNS = [
    "approximate_flat_age_years",
    "remaining_lease_years",
    "lease_timing_anomaly",
]


def add_common_features(
    data,
    dataset_name,
    date_column,
    expected_rows,
):
    conflicting_columns = (
        set(COMMON_FEATURE_COLUMNS)
        & set(data.columns)
    )

    if conflicting_columns:
        raise ValueError(
            f"{dataset_name} already contains analysis features: "
            f"{sorted(conflicting_columns)}"
        )

    dates = pd.to_datetime(
        data[date_column],
        format="%Y-%m-%d",
        errors="raise",
    )

    featured = data.copy()

    featured["calendar_year"] = (
        dates.dt.year.astype("int64")
    )

    featured["calendar_month"] = (
        dates.dt.month.astype("int64")
    )

    featured["calendar_quarter"] = (
        dates.dt.quarter.astype("int64")
    )

    featured["train_distance_band"] = (
        pd.cut(
            featured["nearest_train_distance_km"],
            bins=DISTANCE_BINS,
            labels=DISTANCE_LABELS,
            right=True,
            include_lowest=True,
        )
        .astype("string")
        .fillna("unmatched")
    )

    featured["train_within_800m"] = (
        featured["nearest_train_distance_km"]
        .le(0.8)
        .fillna(False)
        .astype("bool")
    )

    matched = (
        featured["train_proximity_match_status"]
        == "matched"
    )

    unmatched = (
        featured["train_proximity_match_status"]
        == "unmatched"
    )

    expected_band = (
        pd.cut(
            featured["nearest_train_distance_km"],
            bins=DISTANCE_BINS,
            labels=DISTANCE_LABELS,
            right=True,
            include_lowest=True,
        )
        .astype("string")
        .fillna("unmatched")
    )

    expected_within_800m = (
        featured["nearest_train_distance_km"]
        .le(0.8)
        .fillna(False)
        .astype("bool")
    )

    checks = {
        "Expected row count": (
            len(featured) == expected_rows
        ),
        "Row count preserved": (
            len(featured) == len(data)
        ),
        "Source row IDs remain unique": (
            not featured["source_row_id"]
            .duplicated()
            .any()
        ),
        "Calendar features are complete": (
            featured[
                [
                    "calendar_year",
                    "calendar_month",
                    "calendar_quarter",
                ]
            ]
            .notna()
            .all()
            .all()
        ),
        "Calendar years match source dates": (
            featured["calendar_year"]
            .eq(dates.dt.year)
            .all()
        ),
        "Calendar months match source dates": (
            featured["calendar_month"]
            .eq(dates.dt.month)
            .all()
        ),
        "Calendar quarters match source dates": (
            featured["calendar_quarter"]
            .eq(dates.dt.quarter)
            .all()
        ),
        "Distance bands match distances": (
            featured["train_distance_band"]
            .eq(expected_band)
            .all()
        ),
        "Matched rows have distance bands": (
            featured.loc[
                matched,
                "train_distance_band",
            ]
            .isin(DISTANCE_LABELS)
            .all()
        ),
        "Unmatched rows use unmatched band": (
            featured.loc[
                unmatched,
                "train_distance_band",
            ]
            .eq("unmatched")
            .all()
        ),
        "Within-800m indicator is consistent": (
            featured["train_within_800m"]
            .eq(expected_within_800m)
            .all()
        ),
    }

    print(f"\n{'=' * 72}")
    print(f"{dataset_name} common features")
    print(f"Rows: {len(featured):,}")

    print("\nValidation checks:")

    for name, passed in checks.items():
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print("\nTrain-distance bands:")
    print(
        featured["train_distance_band"]
        .value_counts()
        .reindex(
            DISTANCE_LABELS + ["unmatched"],
            fill_value=0,
        )
        .to_string()
    )

    print("\nWithin 800 metres:")
    print(
        featured["train_within_800m"]
        .value_counts()
        .rename(
            index={
                True: "yes",
                False: "no",
            }
        )
        .to_string()
    )

    if not all(checks.values()):
        raise ValueError(
            f"{dataset_name} common-feature validation failed."
        )

    return featured


def add_resale_features(data):
    conflicting_columns = (
        set(RESALE_FEATURE_COLUMNS)
        & set(data.columns)
    )

    if conflicting_columns:
        raise ValueError(
            "Resale already contains derived analysis features: "
            f"{sorted(conflicting_columns)}"
        )

    featured = data.copy()

    featured["approximate_flat_age_years"] = (
        featured["calendar_year"]
        - featured["lease_commence_date"]
    ).astype("int64")

    featured["remaining_lease_years"] = (
        featured["remaining_lease_months"]
        / 12
    ).round(6)

    implied_lease_age_years = (
        99
        - featured["remaining_lease_years"]
    )

    age_difference_years = (
        implied_lease_age_years
        - featured["approximate_flat_age_years"]
    )

    featured["lease_timing_anomaly"] = (
        age_difference_years.abs() > 1
    ).astype("bool")

    checks = {
        "Approximate flat age is complete": (
            featured["approximate_flat_age_years"]
            .notna()
            .all()
        ),
        "Approximate flat age is non-negative": (
            featured["approximate_flat_age_years"]
            .ge(0)
            .all()
        ),
        "Remaining lease years are complete": (
            featured["remaining_lease_years"]
            .notna()
            .all()
        ),
        "Remaining lease years are positive": (
            featured["remaining_lease_years"]
            .gt(0)
            .all()
        ),
        "Remaining lease years do not exceed 99": (
            featured["remaining_lease_years"]
            .le(99)
            .all()
        ),
        "Remaining lease conversion is consistent": (
            np.allclose(
                featured["remaining_lease_years"],
                featured["remaining_lease_months"] / 12,
                rtol=0.0,
                atol=0.000001,
            )
        ),
        "Expected lease-timing anomaly count": (
            featured["lease_timing_anomaly"].sum()
            == 136
        ),
    }

    print("\nResale-specific features")

    print("\nValidation checks:")

    for name, passed in checks.items():
        print(
            f"{name}: "
            f"{'PASS' if passed else 'FAIL'}"
        )

    print("\nApproximate flat-age summary:")
    print(
        featured["approximate_flat_age_years"]
        .describe()
        .to_string()
    )

    print("\nRemaining-lease-years summary:")
    print(
        featured["remaining_lease_years"]
        .describe()
        .to_string()
    )

    print(
        "\nLease-timing anomalies: "
        f"{featured['lease_timing_anomaly'].sum():,}"
    )

    if not all(checks.values()):
        raise ValueError(
            "Resale-specific feature validation failed."
        )

    return featured


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Create analysis-ready HDB rental and resale "
            "datasets with calendar, train-distance and "
            "lease-related features."
        )
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

    rental = pd.read_csv(
        args.rental_input,
        dtype={
            "source_row_id": "string",
            "approval_month": "string",
            "train_proximity_match_status": "string",
        },
    )

    resale = pd.read_csv(
        args.resale_input,
        dtype={
            "source_row_id": "string",
            "transaction_month": "string",
            "train_proximity_match_status": "string",
        },
    )

    rental_featured = add_common_features(
        data=rental,
        dataset_name="Rental",
        date_column="approval_month",
        expected_rows=203_725,
    )

    resale_featured = add_common_features(
        data=resale,
        dataset_name="Resale",
        date_column="transaction_month",
        expected_rows=236_959,
    )

    resale_featured = add_resale_features(
        resale_featured
    )

    args.rental_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    args.resale_output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    rental_featured.to_csv(
        args.rental_output,
        index=False,
        float_format="%.6f",
    )

    resale_featured.to_csv(
        args.resale_output,
        index=False,
        float_format="%.6f",
    )

    print("\nSaved analysis-ready rental dataset to:")
    print(args.rental_output)

    print("\nSaved analysis-ready resale dataset to:")
    print(args.resale_output)


if __name__ == "__main__":
    main()