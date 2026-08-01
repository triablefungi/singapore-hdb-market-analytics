import os

from dotenv import load_dotenv
from sqlalchemy import URL, create_engine, text


load_dotenv()

database_url = URL.create(
    drivername="postgresql+psycopg",
    username=os.getenv("POSTGRES_USER"),
    password=os.getenv("POSTGRES_PASSWORD"),
    host=os.getenv("POSTGRES_HOST"),
    port=int(os.getenv("POSTGRES_PORT", "5432")),
    database=os.getenv("POSTGRES_DB"),
)

engine = create_engine(database_url)

with engine.connect() as connection:
    result = connection.execute(
        text("SELECT current_database(), current_user, version();")
    ).one()

print(f"Connected to database: {result[0]}")
print(f"Connected as user: {result[1]}")
print(f"PostgreSQL version: {result[2]}")