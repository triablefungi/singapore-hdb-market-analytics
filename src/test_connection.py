from sqlalchemy import text

from src.database import engine


def main() -> None:
    with engine.connect() as connection:
        result = connection.execute(
            text(
                """
                SELECT
                    current_database(),
                    current_user,
                    version()
                """
            )
        ).one()

        print(f"Connected to database: {result[0]}")
        print(f"Connected as user: {result[1]}")
        print(f"PostgreSQL version: {result[2]}")

    engine.dispose()


if __name__ == "__main__":
    main()