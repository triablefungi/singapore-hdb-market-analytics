from sqlalchemy import inspect

from src.database import engine
from src.models import Base


def main() -> None:
    Base.metadata.create_all(engine)

    tables = sorted(inspect(engine).get_table_names())

    print("Database schema initialized")
    print(f"Tables: {tables}")

    engine.dispose()


if __name__ == "__main__":
    main()