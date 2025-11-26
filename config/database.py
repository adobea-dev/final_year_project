from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
import duckdb

Base = declarative_base()

class DatabaseConfig:
    """
    Provides connections to both Postgres and DuckDB.
    """

    POSTGRES_URL = "postgresql+psycopg2://postgres:Autochek123@127.0.0.1:5432/dealer_ai"


    _engine = None
    _SessionLocal = None

    @staticmethod
    def get_postgres_engine():
        if DatabaseConfig._engine is None:
            DatabaseConfig._engine = create_engine(DatabaseConfig.POSTGRES_URL, pool_pre_ping=True)
        return DatabaseConfig._engine

    @staticmethod
    def get_postgres_session():
        if DatabaseConfig._SessionLocal is None:
            engine = DatabaseConfig.get_postgres_engine()
            DatabaseConfig._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
        return DatabaseConfig._SessionLocal()

    DUCKDB_PATH = "analytics.duckdb"

    @staticmethod
    def get_duckdb_connection():
        return duckdb.connect(DatabaseConfig.DUCKDB_PATH)
