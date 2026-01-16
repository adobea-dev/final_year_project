# scripts/test_data_agent.py

from agents.data_agent import DataAgent


def main():
    a = DataAgent()
    result = a.run_sql_as_dicts(
        "select dealer_id, country from dealers limit 5"
    )
    print(result)


if __name__ == "__main__":
    main()
