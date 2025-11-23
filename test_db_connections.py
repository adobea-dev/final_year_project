from sqlalchemy import text
from config.database import DatabaseConfig


def test_postgres():
    print("Testing Postgres connection...")
    engine = DatabaseConfig.get_postgres_engine()

    with engine.connect() as conn:
        result = conn.execute(text("SELECT current_database(), current_user"))
        db_name, user_name = result.fetchone()
        print(f"Connected to Postgres DB: {db_name} as user: {user_name}")

        result = conn.execute(text("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """))
        print("Public tables:")
        for row in result:
            print("  -", row.table_name)


def test_duckdb():
    print("\nTesting DuckDB connection...")
    con = DatabaseConfig.get_duckdb_connection()
    res = con.execute("SELECT 1 AS ok").fetchone()
    print("DuckDB result:", res)


if __name__ == "__main__":
    test_postgres()
    test_duckdb()
