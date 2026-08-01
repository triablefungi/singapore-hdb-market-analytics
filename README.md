# Singapore HDB Market Analytics

An end-to-end data analytics and engineering project examining Singapore's HDB resale market, rental market, and MRT accessibility.

## Project objectives

This project aims to answer questions such as:

- How have HDB resale prices and rents changed over time?
- Which towns and flat types have the highest indicative gross rental yields?
- How does proximity to MRT stations relate to resale prices?
- Where are resale prices increasing faster than rents?
- Which areas appear comparatively undervalued after accounting for property characteristics?

## Technology stack

- Python
- pandas
- PostgreSQL
- SQLAlchemy
- psycopg
- Docker Compose
- Tableau Public
- Git and GitHub

## Data pipeline

The project currently includes:

1. Data acquisition from Singapore public-data sources
2. Raw-data profiling and quality assessment
3. Data cleaning, transformation, and validation
4. PostgreSQL schema creation with constraints and indexes
5. Transactional loading of cleaned datasets
6. Row-count and duplicate-load validation

## Database tables

| Table | Description |
|---|---|
| `hdb_resale` | HDB resale transactions and derived property metrics |
| `hdb_rental` | Approved HDB rental records |
| `mrt_exits` | MRT station exits and geographical coordinates |

## Project structure

singapore-hdb-market-analytics/
|
|-- data/
|   |-- raw/
|   |   |-- .gitkeep
|   |   |-- hdb_rental.csv
|   |   |-- hdb_resale.csv
|   |   `-- mrt_exits.geojson
|   `-- processed/
|       |-- .gitkeep
|       |-- hdb_rental_clean.csv
|       |-- hdb_resale_clean.csv
|       `-- mrt_exits_clean.csv
|
|-- sql/
|   `-- analysis/
|       |-- 01_fully_adjusted_yield_exceptions.sql
|       |-- 02_annual_market_yields.sql
|       |-- 03_2025_yield_compression_summary.sql
|       `-- 04_2025_yield_change_details.sql
|
|-- src/
|   |-- clean_data.py
|   |-- config.py
|   |-- database.py
|   |-- download_data.py
|   |-- init_db.py
|   |-- load_data.py
|   |-- models.py
|   `-- test_connection.py
|
|-- .env.example
|-- .gitignore
|-- README.md
`-- requirements.txt

## Methodology

1. Acquire the HDB resale, rental and MRT-location datasets.
2. Clean and validate the raw data before loading it into PostgreSQL.
3. Calculate annual median resale prices and monthly rents by town and flat type.
4. Estimate gross rental yield using:

   `Median monthly rent x 12 / median resale price x 100`

5. Compare 2024 and 2025 results using only combinations with at least 50 resale records and 50 rental records in both years.
6. Investigate apparent yield increases for changes in lease-age and street composition.
7. Apply fixed 2024 lease-band and street-level weights to the remaining exceptions.

Gross rental yield is used as a comparative market indicator. It does not account for financing costs, taxes, maintenance, vacancies or other ownership expenses.

## Key Findings

Among the 88 town-flat type combinations meeting the minimum sample-size requirement:

- 83 combinations (94.32%) recorded declining gross rental yields from 2024 to 2025.
- 5 combinations (5.68%) initially appeared to record rising yields.
- After controlling for lease-age and street composition using fixed 2024 weights, only 2 combinations retained positive yield changes.

| Town and flat type | Adjusted yield 2024 | Adjusted yield 2025 | Change |
|---|---:|---:|---:|
| Geylang - 5 Room | 5.12% | 5.42% | +0.30 percentage points |
| Bukit Batok - Executive | 5.23% | 5.31% | +0.08 percentage points |

The results indicate broad rental-yield compression across the eligible HDB market segments in 2025. They also demonstrate why apparent changes should be tested for differences in the underlying property and rental mix before being interpreted as genuine market movements.

## Local setup

### 1. Create and activate a virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### 2. Configure environment variables

Create a `.env` file in the project root:

```dotenv
POSTGRES_DB=hdb_market
POSTGRES_USER=hdb_user
POSTGRES_PASSWORD=your_secure_password
POSTGRES_HOST=127.0.0.1
POSTGRES_PORT=5433
```

The `.env` file is excluded from Git and must not be committed.

### 3. Start PostgreSQL

```powershell
docker compose up -d postgres
docker compose ps
```

### 4. Prepare the datasets

```powershell
python -m src.acquire_data
python -m src.profile_data
python -m src.clean_data
```

### 5. Initialize and load the database

```powershell
python -m src.test_connection
python -m src.init_db
python -m src.load_data
```

The loader validates table columns and row counts and prevents accidental duplicate loads.

## Project status

Data acquisition, profiling, cleaning, validation, database modelling, PostgreSQL loading, and the core SQL market analysis are complete. The completed analysis covers annual gross rental yields, 2025 yield compression, minimum sample-size filtering, and adjusted exception testing for lease-age and street composition. MRT proximity analysis, predictive modelling, and dashboard development remain planned.