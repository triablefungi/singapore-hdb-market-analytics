import os

from dotenv import load_dotenv
load_dotenv()

from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
RAW_DATA_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DATA_DIR = PROJECT_ROOT / "data" / "processed"

DATA_GOV_BASE_URL = "https://api-open.data.gov.sg/v1/public/api/datasets"

DATASETS = {
    "hdb_resale": {
        "dataset_id": "d_8b84c4ee58e3cfc0ece0d773c8ca6abc",
        "filename": "hdb_resale.csv",
    },
    "hdb_rental": {
        "dataset_id": "d_c9f57187485a850908655db0e8cfe651",
        "filename": "hdb_rental.csv",
    },
    "mrt_exits": {
        "dataset_id": "d_b39d3a0871985372d7e1637193335da5",
        "filename": "mrt_exits.geojson",
    },
}

POSTGRES_DB = os.environ["POSTGRES_DB"]
POSTGRES_USER = os.environ["POSTGRES_USER"]
POSTGRES_PASSWORD = os.environ["POSTGRES_PASSWORD"]
POSTGRES_HOST = os.getenv("POSTGRES_HOST", "127.0.0.1")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5433"))

DATABASE_URL = (
    f"postgresql+psycopg://{POSTGRES_USER}:"
    f"{POSTGRES_PASSWORD}@{POSTGRES_HOST}:"
    f"{POSTGRES_PORT}/{POSTGRES_DB}"
)