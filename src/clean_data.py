import json

import pandas as pd

from src.config import PROCESSED_DATA_DIR, RAW_DATA_DIR


def clean_resale_data() -> pd.DataFrame:
    df = pd.read_csv(RAW_DATA_DIR / "hdb_resale.csv")

    df.insert(0, "source_row_id", range(1, len(df) + 1))

    df["transaction_month"] = pd.to_datetime(
        df.pop("month"),
        format="%Y-%m",
        errors="raise",
    )

    text_columns = [
        "town",
        "flat_type",
        "block",
        "street_name",
        "storey_range",
        "flat_model",
        "remaining_lease",
    ]

    for column in text_columns:
        df[column] = df[column].str.strip()

    df["address"] = df["block"] + " " + df["street_name"]

    lease_parts = df["remaining_lease"].str.extract(
        r"^(?P<years>\d+) years?(?: (?P<months>\d+) months?)?$"
    )

    df["remaining_lease_months"] = (
        pd.to_numeric(lease_parts["years"]) * 12
        + pd.to_numeric(lease_parts["months"]).fillna(0)
    ).astype("int64")

    storey_parts = df["storey_range"].str.extract(
        r"^(?P<storey_lower>\d+) TO (?P<storey_upper>\d+)$"
    )

    df["storey_lower"] = pd.to_numeric(
        storey_parts["storey_lower"]
    ).astype("int64")

    df["storey_upper"] = pd.to_numeric(
        storey_parts["storey_upper"]
    ).astype("int64")

    df["storey_midpoint"] = (
        df["storey_lower"] + df["storey_upper"]
    ) / 2

    df["floor_area_sqm"] = pd.to_numeric(
        df["floor_area_sqm"],
        errors="raise",
    )

    df["resale_price"] = pd.to_numeric(
        df["resale_price"],
        errors="raise",
    )

    df["lease_commence_date"] = pd.to_numeric(
        df["lease_commence_date"],
        errors="raise",
    ).astype("int64")

    df["price_per_sqm"] = (
        df["resale_price"] / df["floor_area_sqm"]
    ).round(2)

    assert df["transaction_month"].notna().all()
    assert (df["floor_area_sqm"] > 0).all()
    assert (df["resale_price"] > 0).all()
    assert df["remaining_lease_months"].between(0, 99 * 12).all()

    return df


def clean_rental_data() -> pd.DataFrame:
    df = pd.read_csv(RAW_DATA_DIR / "hdb_rental.csv")

    df.insert(0, "source_row_id", range(1, len(df) + 1))

    df["approval_month"] = pd.to_datetime(
        df.pop("rent_approval_date"),
        format="%Y-%m",
        errors="raise",
    )

    text_columns = [
        "town",
        "block",
        "street_name",
        "flat_type",
    ]

    for column in text_columns:
        df[column] = df[column].str.strip()

    df["town"] = df["town"].replace({"CENTRAL": "CENTRAL AREA"})
    df["address"] = df["block"] + " " + df["street_name"]

    df["monthly_rent"] = pd.to_numeric(
        df["monthly_rent"],
        errors="raise",
    )

    assert df["approval_month"].notna().all()
    assert (df["monthly_rent"] > 0).all()

    return df


def clean_mrt_exit_data() -> pd.DataFrame:
    path = RAW_DATA_DIR / "mrt_exits.geojson"
    data = json.loads(path.read_text(encoding="utf-8"))

    rows = []

    for source_row_id, feature in enumerate(data["features"], start=1):
        properties = {
            key.strip('"'): value
            for key, value in feature["properties"].items()
        }

        longitude, latitude = feature["geometry"]["coordinates"]

        rows.append(
            {
                "source_row_id": source_row_id,
                "station_name": properties.get("STATION_NA"),
                "exit_code": properties.get("EXIT_CODE"),
                "longitude": longitude,
                "latitude": latitude,
            }
        )

    df = pd.DataFrame(rows)

    df["station_name"] = df["station_name"].str.strip()
    df["exit_code"] = df["exit_code"].str.strip()
    df["longitude"] = pd.to_numeric(df["longitude"], errors="raise")
    df["latitude"] = pd.to_numeric(df["latitude"], errors="raise")

    assert df["station_name"].notna().all()
    assert df["exit_code"].notna().all()
    assert df["longitude"].between(103, 105).all()
    assert df["latitude"].between(1, 2).all()

    return df


def main() -> None:
    PROCESSED_DATA_DIR.mkdir(parents=True, exist_ok=True)

    datasets = {
        "hdb_resale_clean.csv": clean_resale_data(),
        "hdb_rental_clean.csv": clean_rental_data(),
        "mrt_exits_clean.csv": clean_mrt_exit_data(),
    }

    for filename, dataframe in datasets.items():
        destination = PROCESSED_DATA_DIR / filename
        dataframe.to_csv(destination, index=False)

        print(
            f"Created {filename}: "
            f"{len(dataframe):,} rows, "
            f"{len(dataframe.columns)} columns"
        )


if __name__ == "__main__":
    main()