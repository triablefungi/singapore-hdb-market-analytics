import argparse
import os
import re
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


PROCESSED_DATA_DIR = Path("data/processed")

INPUT_PATH = PROCESSED_DATA_DIR / "hdb_addresses_to_geocode.csv"
OUTPUT_PATH = PROCESSED_DATA_DIR / "hdb_address_geocodes.csv"

AUTH_URL = "https://www.onemap.gov.sg/api/auth/post/getToken"
SEARCH_URL = "https://www.onemap.gov.sg/api/common/elastic/search"

CHECKPOINT_INTERVAL = 25
DEFAULT_DELAY_SECONDS = 0.5
REQUEST_TIMEOUT_SECONDS = 30

TERMINAL_STATUSES = {
    "matched",
    "no_results",
    "no_exact_match",
}

RESULT_COLUMNS = [
    "search_query",
    "matched_address",
    "building",
    "block",
    "road",
    "postal_code",
    "latitude",
    "longitude",
    "x_coordinate",
    "y_coordinate",
    "match_status",
    "candidate_count",
    "error_message",
    "geocoded_at_utc",
]

ADDRESS_ABBREVIATIONS = {
    "AVE": "AVENUE",
    "BT": "BUKIT",
    "CL": "CLOSE",
    "CRES": "CRESCENT",
    "CTRL": "CENTRAL",
    "DR": "DRIVE",
    "GDN": "GARDEN",
    "GDNS": "GARDENS",
    "HGTS": "HEIGHTS",
    "HTS": "HEIGHTS",
    "HWY": "HIGHWAY",
    "JLN": "JALAN",
    "KG": "KAMPONG",
    "LOR": "LORONG",
    "MKT": "MARKET",
    "NTH": "NORTH",
    "PK": "PARK",
    "PL": "PLACE",
    "RD": "ROAD",
    "ST": "STREET",
    "STH": "SOUTH",
    "TER": "TERRACE",
    "UPP": "UPPER",
}


def parse_arguments() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Geocode unique HDB addresses using OneMap."
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Maximum number of pending addresses to process.",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=DEFAULT_DELAY_SECONDS,
        help="Delay between Search API requests in seconds.",
    )
    parser.add_argument(
        "--retry-unmatched",
        action="store_true",
        help="Retry saved no-result and non-exact matches.",
    )
    return parser.parse_args()


def create_session() -> requests.Session:
    retry_policy = Retry(
        total=5,
        connect=5,
        read=5,
        status=5,
        backoff_factor=1,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET"]),
        respect_retry_after_header=True,
        raise_on_status=False,
    )

    adapter = HTTPAdapter(max_retries=retry_policy)

    session = requests.Session()
    session.mount("https://", adapter)
    session.headers.update(
        {"User-Agent": "singapore-hdb-market-analytics/1.0"}
    )

    return session


def get_access_token(
    session: requests.Session,
    email: str,
    password: str,
) -> str:
    response = session.post(
        AUTH_URL,
        json={
            "email": email,
            "password": password,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()

    payload = response.json()
    token = payload.get("access_token")

    if not token:
        raise RuntimeError(
            "OneMap authentication response did not contain an access token."
        )

    return token


def normalise_address(value: object) -> str:
    if pd.isna(value):
        return ""

    address = str(value).strip().upper()
    address = re.sub(r"[^A-Z0-9\s]", " ", address)
    address = re.sub(r"\s+", " ", address).strip()

    phrase_replacements = {
        r"\bC WEALTH\b": "COMMONWEALTH",
        r"\bTG PAGAR\b": "TANJONG PAGAR",
        r"\bST GEORGE S\b": "SAINT GEORGE S",
    }

    for pattern, replacement in phrase_replacements.items():
        address = re.sub(pattern, replacement, address)

    tokens = address.split()

    expanded_tokens = [
        ADDRESS_ABBREVIATIONS.get(token, token)
        for token in tokens
    ]

    return " ".join(expanded_tokens)


def candidate_address_key(candidate: dict) -> str:
    block = candidate.get("BLK_NO", "")
    road = candidate.get("ROAD_NAME", "")
    return normalise_address(f"{block} {road}")


def search_address(
    session: requests.Session,
    token: str,
    address: str,
) -> tuple[dict, str]:
    params = {
        "searchVal": address,
        "returnGeom": "Y",
        "getAddrDetails": "Y",
        "pageNum": 1,
    }

    response = session.get(
        SEARCH_URL,
        params=params,
        headers={"Authorization": token},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )

    if response.status_code == 401:
        return {}, "token_expired"

    response.raise_for_status()
    return response.json(), "ok"


def select_result(address: str, payload: dict) -> dict:
    candidates = payload.get("results") or []
    candidate_count = len(candidates)

    base_result = {
        "search_query": address,
        "matched_address": "",
        "building": "",
        "block": "",
        "road": "",
        "postal_code": "",
        "latitude": pd.NA,
        "longitude": pd.NA,
        "x_coordinate": pd.NA,
        "y_coordinate": pd.NA,
        "match_status": "",
        "candidate_count": candidate_count,
        "error_message": "",
        "geocoded_at_utc": datetime.now(timezone.utc).isoformat(),
    }

    if not candidates:
        base_result["match_status"] = "no_results"
        return base_result

    query_key = normalise_address(address)

    exact_candidates = [
        candidate
        for candidate in candidates
        if candidate_address_key(candidate) == query_key
    ]

    if not exact_candidates:
        first_candidate = candidates[0]

        base_result.update(
            {
                "matched_address": first_candidate.get("ADDRESS", ""),
                "building": first_candidate.get("BUILDING", ""),
                "block": first_candidate.get("BLK_NO", ""),
                "road": first_candidate.get("ROAD_NAME", ""),
                "postal_code": first_candidate.get("POSTAL", ""),
                "match_status": "no_exact_match",
            }
        )
        return base_result

    selected = exact_candidates[0]

    base_result.update(
        {
            "matched_address": selected.get("ADDRESS", ""),
            "building": selected.get("BUILDING", ""),
            "block": selected.get("BLK_NO", ""),
            "road": selected.get("ROAD_NAME", ""),
            "postal_code": selected.get("POSTAL", ""),
            "latitude": selected.get("LATITUDE", pd.NA),
            "longitude": selected.get("LONGITUDE", pd.NA),
            "x_coordinate": selected.get("X", pd.NA),
            "y_coordinate": selected.get("Y", pd.NA),
            "match_status": "matched",
        }
    )

    return base_result


def load_working_data() -> pd.DataFrame:
    addresses = pd.read_csv(
        INPUT_PATH,
        dtype={"address": "string"},
    )

    if addresses["address"].duplicated().any():
        raise ValueError("The input address file contains duplicates.")

    for column in RESULT_COLUMNS:
        addresses[column] = pd.NA

    if not OUTPUT_PATH.exists():
        return addresses

    saved = pd.read_csv(
        OUTPUT_PATH,
        dtype={"address": "string"},
    )

    if saved["address"].duplicated().any():
        raise ValueError("The saved geocode file contains duplicates.")

    saved = saved.set_index("address")

    for column in RESULT_COLUMNS:
        if column in saved.columns:
            addresses[column] = addresses["address"].map(saved[column])

    return addresses


def save_checkpoint(data: pd.DataFrame) -> None:
    temporary_path = OUTPUT_PATH.with_suffix(".csv.tmp")

    data.to_csv(
        temporary_path,
        index=False,
        encoding="utf-8",
        lineterminator="\n",
    )

    os.replace(temporary_path, OUTPUT_PATH)


def main() -> None:
    args = parse_arguments()

    if args.limit is not None and args.limit < 1:
        raise ValueError("--limit must be at least 1.")

    if args.delay < 0:
        raise ValueError("--delay cannot be negative.")

    load_dotenv()

    email = os.getenv("ONEMAP_EMAIL")
    password = os.getenv("ONEMAP_PASSWORD")

    if not email or not password:
        raise RuntimeError(
            "ONEMAP_EMAIL and ONEMAP_PASSWORD must be configured in .env."
        )

    data = load_working_data()
    data[RESULT_COLUMNS] = data[RESULT_COLUMNS].astype("object")

    if args.retry_unmatched:
        completed_statuses = {"matched"}
    else:
        completed_statuses = TERMINAL_STATUSES

    pending_indices = data.index[
        ~data["match_status"].isin(completed_statuses)
    ].tolist()

    if args.limit is not None:
        pending_indices = pending_indices[:args.limit]

    print(f"Total addresses: {len(data):,}")
    print(f"Addresses selected this run: {len(pending_indices):,}")

    if not pending_indices:
        print("No pending addresses to process.")
        return

    session = create_session()
    token = get_access_token(session, email, password)

    processed_this_run = 0

    try:
        for index in pending_indices:
            address = str(data.at[index, "address"])

            try:
                payload, request_status = search_address(
                    session,
                    token,
                    address,
                )

                if request_status == "token_expired":
                    token = get_access_token(
                        session,
                        email,
                        password,
                    )
                    payload, request_status = search_address(
                        session,
                        token,
                        address,
                    )

                if request_status != "ok":
                    raise RuntimeError(
                        f"Unexpected request status: {request_status}"
                    )

                result = select_result(address, payload)

            except (
                requests.RequestException,
                RuntimeError,
                ValueError,
            ) as error:
                result = {
                    "search_query": address,
                    "matched_address": "",
                    "building": "",
                    "block": "",
                    "road": "",
                    "postal_code": "",
                    "latitude": pd.NA,
                    "longitude": pd.NA,
                    "x_coordinate": pd.NA,
                    "y_coordinate": pd.NA,
                    "match_status": "error",
                    "candidate_count": pd.NA,
                    "error_message": (
                        f"{type(error).__name__}: {error}"
                    ),
                    "geocoded_at_utc": (
                        datetime.now(timezone.utc).isoformat()
                    ),
                }

            for column, value in result.items():
                data.at[index, column] = value

            processed_this_run += 1

            print(
                f"[{processed_this_run:,}/{len(pending_indices):,}] "
                f"{address}: {result['match_status']}"
            )

            if processed_this_run % CHECKPOINT_INTERVAL == 0:
                save_checkpoint(data)
                print("Checkpoint saved.")

            if args.delay:
                time.sleep(args.delay)

    except KeyboardInterrupt:
        print("\nInterrupted by user. Saving progress before exit.")

    finally:
        save_checkpoint(data)
        session.close()

    print(f"\nOutput file: {OUTPUT_PATH}")
    print(f"Processed this run: {processed_this_run:,}")
    print("\nCurrent status counts:")
    print(
        data["match_status"]
        .fillna("pending")
        .value_counts(dropna=False)
        .to_string()
    )


if __name__ == "__main__":
    main()