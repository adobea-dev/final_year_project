from __future__ import annotations

import sys
from pathlib import Path

# Ensures imports work when running: python -m scripts.create_tables
PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.database import DatabaseConfig, Base  
import database.models  


def main() -> None:
    engine = DatabaseConfig.get_postgres_engine()
    Base.metadata.create_all(bind=engine)
    print("Tables created successfully in Postgres.")


if __name__ == "__main__":
    main()
