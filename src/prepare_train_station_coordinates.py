import argparse
from collections import defaultdict
from pathlib import Path

import pandas as pd
import pyproj
import shapefile


DEFAULT_SHAPEFILE_PATH = Path(
    "data/raw/lta_train_stations/extracted/"
    "TrainStation_Mar2026/"
    "RapidTransitSystemStation.shp"
)

DEFAULT_OUTPUT_PATH = Path(
    "data/processed/train_station_coordinates.csv"
)

CCL6_STATIONS = [
    {
        "station_name": "CANTONMENT MRT STATION",
        "station_type": "MRT",
        "latitude": 1.27287214563203,
        "longitude": 103.837062313764,
    },
    {
        "station_name": "KEPPEL MRT STATION",
        "station_type": "MRT",
        "latitude": 1.26977220124441,
        "longitude": 103.830031459524,
    },
    {
        "station_name": "PRINCE EDWARD ROAD MRT STATION",
        "station_type": "MRT",
        "latitude": 1.27315693636085,
        "longitude": 103.847097123745,
    },
]


def ring_centroid(points):
    if len(points) < 3:
        return None

    if points[0] != points[-1]:
        points = [*points, points[0]]

    twice_area = 0.0
    x_sum = 0.0
    y_sum = 0.0

    for first, second in zip(points, points[1:]):
        x1, y1 = first
        x2, y2 = second
        cross = (x1 * y2) - (x2 * y1)

        twice_area += cross
        x_sum += (x1 + x2) * cross
        y_sum += (y1 + y2) * cross

    if abs(twice_area) < 1e-9:
        return None

    signed_area = twice_area / 2.0
    centroid_x = x_sum / (3.0 * twice_area)
    centroid_y = y_sum / (3.0 * twice_area)

    return signed_area, centroid_x, centroid_y


def polygon_centroid(shape):
    points = shape.points
    starts = list(shape.parts) + [len(points)]

    ring_results = []

    for start, end in zip(starts, starts[1:]):
        result = ring_centroid(points[start:end])

        if result is not None:
            ring_results.append(result)

    if not ring_results:
        min_x, min_y, max_x, max_y = shape.bbox

        return (
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            1.0,
        )

    total_signed_area = sum(
        result[0] for result in ring_results
    )

    if abs(total_signed_area) < 1e-9:
        min_x, min_y, max_x, max_y = shape.bbox

        return (
            (min_x + max_x) / 2.0,
            (min_y + max_y) / 2.0,
            1.0,
        )

    centroid_x = sum(
        area * x
        for area, x, _ in ring_results
    ) / total_signed_area

    centroid_y = sum(
        area * y
        for area, _, y in ring_results
    ) / total_signed_area

    return (
        centroid_x,
        centroid_y,
        abs(total_signed_area),
    )


def prepare_station_coordinates(shapefile_path):
    transformer = pyproj.Transformer.from_crs(
        "EPSG:3414",
        "EPSG:4326",
        always_xy=True,
    )

    records_by_name = defaultdict(list)

    with shapefile.Reader(
        str(shapefile_path),
        encoding="utf-8",
    ) as reader:
        for shape_record in reader.iterShapeRecords():
            attributes = shape_record.record.as_dict()

            station_name = str(
                attributes.get("STN_NAM_DE", "")
            ).strip()

            station_type = str(
                attributes.get("TYP_CD_DES", "")
            ).strip()

            is_passenger_station = (
                station_name.endswith(" MRT STATION")
                or station_name.endswith(" LRT STATION")
            )

            if not is_passenger_station:
                continue

            x, y, area = polygon_centroid(
                shape_record.shape
            )

            records_by_name[station_name].append(
                {
                    "station_type": station_type,
                    "x": x,
                    "y": y,
                    "area": area,
                }
            )

    prepared_records = []

    for station_name, records in records_by_name.items():
        total_area = sum(
            record["area"] for record in records
        )

        x = sum(
            record["x"] * record["area"]
            for record in records
        ) / total_area

        y = sum(
            record["y"] * record["area"]
            for record in records
        ) / total_area

        longitude, latitude = transformer.transform(
            x,
            y,
        )

        station_types = sorted(
            {
                record["station_type"]
                for record in records
            }
        )

        prepared_records.append(
            {
                "station_name": station_name,
                "station_type": "|".join(station_types),
                "latitude": latitude,
                "longitude": longitude,
                "polygon_count": len(records),
                "coordinate_source": (
                    "LTA Train Station March 2026"
                ),
            }
        )

    for station in CCL6_STATIONS:
        prepared_records.append(
            {
                **station,
                "polygon_count": 0,
                "coordinate_source": (
                    "OneMap search August 2026"
                ),
            }
        )

    return pd.DataFrame(prepared_records)


def validate(data):
    checks = {
        "Total station names are 192": len(data) == 192,
        "Station names are unique": (
            not data["station_name"].duplicated().any()
        ),
        "No missing station names": (
            data["station_name"].notna().all()
        ),
        "No missing station types": (
            data["station_type"].notna().all()
        ),
        "No missing latitudes": (
            data["latitude"].notna().all()
        ),
        "No missing longitudes": (
            data["longitude"].notna().all()
        ),
        "Latitudes within Singapore range": (
            data["latitude"].between(1.1, 1.6).all()
        ),
        "Longitudes within Singapore range": (
            data["longitude"].between(
                103.5,
                104.2,
            ).all()
        ),
        "Three CCL6 supplements present": (
            set(
                station["station_name"]
                for station in CCL6_STATIONS
            ).issubset(set(data["station_name"]))
        ),
    }

    print("Validation checks:")

    for name, passed in checks.items():
        print(f"{name}: {'PASS' if passed else 'FAIL'}")

    if not all(checks.values()):
        raise ValueError(
            "One or more station validation checks failed."
        )


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Prepare operational Singapore train station "
            "coordinates."
        )
    )

    parser.add_argument(
        "--shapefile",
        type=Path,
        default=DEFAULT_SHAPEFILE_PATH,
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
    )

    args = parser.parse_args()

    data = prepare_station_coordinates(
        args.shapefile
    )

    data = data.sort_values(
        ["station_type", "station_name"]
    ).reset_index(drop=True)

    validate(data)

    args.output.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    data.to_csv(
        args.output,
        index=False,
        float_format="%.12f",
    )

    print("\nStation-type counts:")
    print(data["station_type"].value_counts().to_string())

    print("\nCoordinate-source counts:")
    print(
        data["coordinate_source"]
        .value_counts()
        .to_string()
    )

    print("\nSupplemental CCL6 records:")
    print(
        data[
            data["coordinate_source"]
            == "OneMap search August 2026"
        ].to_string(index=False)
    )

    print(f"\nSaved {len(data):,} stations to:")
    print(args.output)


if __name__ == "__main__":
    main()