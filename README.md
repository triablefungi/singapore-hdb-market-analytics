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

```text
data/
├── raw/                    # Original source data
└── processed/              # Cleaned datasets

docs/
└── data_quality.md         # Data-quality findings and cleaning decisions

src/
├── acquire_data.py         # Downloads source datasets
├── clean_data.py           # Cleans and validates raw data
├── config.py               # Project paths and environment settings
├── database.py             # Shared SQLAlchemy database engine
├── init_db.py              # Initializes the PostgreSQL schema
├── load_data.py            # Loads cleaned data into PostgreSQL
├── models.py               # SQLAlchemy table definitions
├── profile_data.py         # Profiles source-data quality
└── test_connection.py      # Tests the PostgreSQL connection
```

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

Data acquisition, profiling, cleaning, validation, database modelling, and PostgreSQL loading are complete. Exploratory analysis, MRT proximity analysis, modelling, and dashboard development are in progress.