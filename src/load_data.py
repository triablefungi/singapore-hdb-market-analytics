import pandas as pd
from sqlalchemy import func, select

from src.config import PROCESSED_DATA_DIR
from src.database import engine
from src.models import HDBRental, HDBResale, MRTExit


DATASETS = (
    (
        HDBResale,
        PROCESSED_DATA_DIR / "hdb_resale_clean.csv",
        ["transaction_month"],
    ),
    (
        HDBRental,
        PROCESSED_DATA_DIR / "hdb_rental_clean.csv",
        ["approval_month"],
    ),
    (
        MRTExit,
        PROCESSED_DATA_DIR / "mrt_exits_clean.csv",
        [],
    ),
)


def load_dataset(
    connection,
    model,
    path,
    date_columns,
) -> None:
    table = model.__table__
    table_name = table.name

    existing_rows = connection.execute(
        select(func.count()).select_from(table)
    ).scalar_one()

    if existing_rows != 0:
        raise RuntimeError(
            f"{table_name} already contains {existing_rows:,} rows"
        )

    dataframe = pd.read_csv(
        path,
        parse_dates=date_columns,
    )

    expected_columns = list(table.columns.keys())
    actual_columns = list(dataframe.columns)

    if set(actual_columns) != set(expected_columns):
        missing = sorted(set(expected_columns) - set(actual_columns))
        unexpected = sorted(set(actual_columns) - set(expected_columns))

        raise ValueError(
            f"Column mismatch for {table_name}. "
            f"Missing: {missing}; unexpected: {unexpected}"
        )

    dataframe = dataframe[expected_columns]

    dataframe.to_sql(
        name=table_name,
        con=connection,
        if_exists="append",
        index=False,
        chunksize=5_000,
    )

    loaded_rows = connection.execute(
        select(func.count()).select_from(table)
    ).scalar_one()

    if loaded_rows != len(dataframe):
        raise RuntimeError(
            f"Row-count mismatch for {table_name}: "
            f"expected {len(dataframe):,}, loaded {loaded_rows:,}"
        )

    print(f"Loaded {table_name}: {loaded_rows:,} rows")


def main() -> None:
    with engine.begin() as connection:
        for model, path, date_columns in DATASETS:
            load_dataset(
                connection,
                model,
                path,
                date_columns,
            )

    engine.dispose()
    print("Database load completed successfully")


if __name__ == "__main__":
    main()