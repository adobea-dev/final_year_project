from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import duckdb

class DatabaseConfig:
    """
    Provides connections to both Postgres and DuckDB.
    """

    # === Postgres Connection ===
    POSTGRES_URL = "postgresql://postgres:Autochek123@localhost:5433/dealer_ai"

    @staticmethod
    def get_postgres_engine():
        """Return a SQLAlchemy engine for Postgres."""
        return create_engine(DatabaseConfig.POSTGRES_URL)

    @staticmethod
    def get_postgres_session():
        """Return a SQLAlchemy session bound to Postgres."""
        engine = DatabaseConfig.get_postgres_engine()
        SessionLocal = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine,
        )
        return SessionLocal()

    # === DuckDB Connection (local analytics DB) ===
    DUCKDB_PATH = "analytics.duckdb"

    @staticmethod
    def get_duckdb_connection():
        """
        Return a DuckDB connection. Creates analytics.duckdb
        in the project folder if it does not exist.
        """
        return duckdb.connect(DatabaseConfig.DUCKDB_PATH)