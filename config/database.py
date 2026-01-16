from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from .settings import settings


class DatabaseConfig:
    # Build the URL from environment driven settings
    POSTGRES_URL = (
        f"postgresql+psycopg2://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )

    _engine = None
    _SessionLocal = None

    @staticmethod
    def get_postgres_engine():
        if DatabaseConfig._engine is None:
            DatabaseConfig._engine = create_engine(
                DatabaseConfig.POSTGRES_URL,
                pool_pre_ping=True,
            )
        return DatabaseConfig._engine

    @staticmethod
    def get_postgres_session():
        if DatabaseConfig._SessionLocal is None:
            engine = DatabaseConfig.get_postgres_engine()
            DatabaseConfig._SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=engine,
            )
        return DatabaseConfig._SessionLocal()
