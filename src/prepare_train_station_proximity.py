import argparse
from pathlib import Path

import numpy as np
import pandas as pd


DEFAULT_ADDRESS_PATH = Path(
    "data/processed/hdb_address_geocodes.csv"
)

DEFAULT_STATION_PATH = Path(
    "data/processed/train_station_coordinates.csv"
)

DEFAULT_OUTPUT_PATH = Path(
    "data/processed/hdb_address_train_proximity.csv"
)

EARTH_RADIUS_KM = 6371.0088


def nearest_stations(addresses, stations):
    address_latitude = np.radians(
        addresses["latitude"].to_numpy(dtype=float)
    )[:, None]

    address_longitude = np.radians(
        addresses["longitude"].to_numpy(dtype=float)
    )[:, None]

    station_latitude = np.radians(
        stations["latitude"].to_numpy(dtype=float)
    )[None, :]

    station_longitude = np.radians(
        stations["longitude"].to_numpy(dtype=float)
    )[None, :]

    latitude_difference = (
        station_latitude - address_latitude
    )

    longitude_difference = (
        station_longitude - address_longitude
    )

    haversine_value = (
        np.sin(latitude_difference / 2.0) ** 2
        + np.cos(address_latitude)
        * np.cos(station_latitude)
        * np.sin(longitude_difference / 2.0) ** 2
    )

    haversine_value = np.clip(
        haversine_value,
        0.0,
        1.0,
    )

    distances = (
        2.0
        * EARTH_RADIUS_KM
        * np.arcsin(np.sqrt(haversine_value))
    )

    nearest_indexes = np.argmin(
        distances,
        axis=1,
    )

    nearest_distances = distances[
        np.arange(len(addresses)),
        nearest_indexes,
    ]

    nearest_records = stations.iloc[
        nearest_indexes
    ].reset_index(drop=True)

    return nearest_records, nearest_distances


def prepare_proximity(address_data, station_data):
    matched = address_data[
        address_data["match_status"] == "matched"
    ].copy().reset_index(drop=True)

    mrt_stations = station_data[
        station_data["station_type"] == "MRT"
    ].copy().reset_index(drop=True)

    lrt_stations = station_data[
        station_data["station_type"] == "LRT"
    ].copy().reset_index(drop=True)

    nearest_train, train_distances = nearest_stations(
        matched,
        station_data,
    )

    nearest_mrt, mrt_distances = nearest_stations(
        matched,
        mrt_stations,
    )

    nearest_lrt, lrt_distances = nearest_stations(
        matched,
        lrt_stations,
    )

    return pd.DataFrame(
        {
            "address": matched["address"],
            "nearest_train_station": (
                nearest_train["station_name"]
            ),
            "nearest_train_type": (
                nearest_train["station_type"]
            ),
            "nearest_train_distance_km": train_distances,
            "nearest_mrt_station": (
                nearest_mrt["station_name"]
            ),
            "nearest_mrt_distance_km": mrt_distances,
            "nearest_lrt_station": (
                nearest_lrt["station_name"]
            ),
            "nearest_lrt_distance_km": lrt_distances,
        }
    )


def validate(data):
    distance_columns = [
        "nearest_train_distance_km",
        "nearest_mrt_distance_km",
        "nearest_lrt_distance_km",
    ]

    station_columns = [
        "nearest_train_station",
        "nearest_mrt_station",
        "nearest_lrt_station",
    ]

    expected_overall_distance = data[
        [
            "nearest_mrt_distance_km",
            "nearest_lrt_distance_km",
        ]
    ].min(axis=1)

    checks = {
        "Matched addresses are 9,987": (
            len(data) == 9_987
        ),
        "Addresses are unique": (
            not data["address"].duplicated().any()
        ),
        "No missing addresses": (
            data["address"].notna().all()
        ),
        "No missing nearest stations": (
            data[station_columns].notna().all().all()
        ),
        "Nearest train types are valid": (
            data["nearest_train_type"]
            .isin(["MRT", "LRT"])
            .all()
        ),
        "No missing distances": (
            data[distance_columns].notna().all().all()
        ),
        "No negative distances": (
            data[distance_columns].ge(0).all().all()
        ),
        "Overall distance equals MRT/LRT minimum": (
            np.allclose(
                data["nearest_train_distance_km"],
                expected_overall_distance,
                rtol=0.0,
                atol=1e-12,
            )
        ),
    }

    print("Validation checks:")

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        raise ValueError(
            "One or more proximity validation checks failed."
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Calculate straight-line distances from matched "
            "HDB addresses to Singapore MRT and LRT stations."
        )
    )

    parser.add_argument(
        "--addresses",
        type=Path,
        default=DEFAULT_ADDRESS_PATH,
    )

    parser.add_argument(
        "--stations",
        type=Path,
        default=DEFAULT_STATION_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    args = parser.parse_args()

    address_data = pd.read_csv(
        args.addresses,
        dtype={"address": "string"},
    )

    station_data = pd.read_csv(
        args.stations,
        dtype={
            "station_name": "string",
            "station_type": "string",
        },
    )

    proximity_data = prepare_proximity(
        address_data,
        station_data,
    )

    proximity_data = proximity_data.sort_values(
        "address"
    ).reset_index(drop=True)

    validate(proximity_data)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    proximity_data.to_csv(
        args.output,
        index=False,
        float_format="%.6f",
    )

    print("\nNearest train-type counts:")
    print(
        proximity_data["nearest_train_type"]
        .value_counts()
        .to_string()
    )

    print("\nNearest-train distance summary (km):")
    print(
        proximity_data["nearest_train_distance_km"]
        .describe(
            percentiles=[
                0.25,
                0.5,
                0.75,
                0.9,
                0.95,
                0.99,
            ]
        )
        .to_string()
    )

    print(f"\nSaved {len(proximity_data):,} address records to:")
    print(args.output)


if __name__ == "__main__":
    main()