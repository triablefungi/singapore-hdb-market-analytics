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