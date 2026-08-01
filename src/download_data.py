import argparse
import time
from pathlib import Path

import requests

from src.config import DATASETS, DATA_GOV_BASE_URL, RAW_DATA_DIR


def get_download_url(dataset_id: str) -> str:
    initiate_url = f"{DATA_GOV_BASE_URL}/{dataset_id}/initiate-download"
    response = requests.get(initiate_url, timeout=30)
    response.raise_for_status()

    data = response.json().get("data", {})
    download_url = data.get("url")

    if download_url:
        return download_url

    poll_url = f"{DATA_GOV_BASE_URL}/{dataset_id}/poll-download"

    for _ in range(12):
        time.sleep(5)
        response = requests.get(poll_url, timeout=30)
        response.raise_for_status()

        data = response.json().get("data", {})
        download_url = data.get("url")

        if download_url:
            return download_url

    raise TimeoutError(f"Download was not ready for dataset {dataset_id}")


def download_file(download_url: str, destination: Path) -> None:
    with requests.get(download_url, stream=True, timeout=120) as response:
        response.raise_for_status()

        with destination.open("wb") as file:
            for chunk in response.iter_content(chunk_size=1024 * 1024):
                if chunk:
                    file.write(chunk)


def download_dataset(dataset_name: str) -> Path:
    dataset = DATASETS[dataset_name]
    destination = RAW_DATA_DIR / dataset["filename"]

    RAW_DATA_DIR.mkdir(parents=True, exist_ok=True)

    print(f"Preparing {dataset_name}...")
    download_url = get_download_url(dataset["dataset_id"])

    print(f"Downloading to {destination}...")
    download_file(download_url, destination)

    print(f"Completed: {destination.stat().st_size:,} bytes")
    return destination


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Download official datasets from data.gov.sg."
    )
    parser.add_argument(
        "dataset",
        choices=[*DATASETS.keys(), "all"],
        help="Dataset to download.",
    )
    args = parser.parse_args()

    selected_datasets = (
        DATASETS.keys() if args.dataset == "all" else [args.dataset]
    )

    for dataset_name in selected_datasets:
        download_dataset(dataset_name)


if __name__ == "__main__":
    main()