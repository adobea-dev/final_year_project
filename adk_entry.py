# adk_entry.py
from __future__ import annotations

import asyncio
from datetime import datetime

from google.genai import types
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService

from agents.dealer_copilot.agent import root_agent
from agents.data_agent import DataAgent
from agents.scoring_agent import score_dealers
from agents.recommendation_agent import recommend_dealer_actions


async def main() -> None:
    # 1. Session service and runner
    session_service = InMemorySessionService()
    runner = Runner(
        agent=root_agent,
        app_name="dealer_copilot",
        session_service=session_service,
    )

    user_id = "local_user"
    session_id = f"session-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    session = await session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id,
    )
    print(f"Session created: {session.id}\n")

    print("Dealer Copilot CLI")
    print("Type your question, or use one of the special commands:")
    print("  sql: <SELECT ...>              run a SQL query on Postgres")
    print("  score: <country_code> [top_n]  compute dealer scores")
    print("  recommend: <country_code>      get dealer recommendations")
    print("Type 'exit' or 'quit' to stop.\n")

    data_agent = DataAgent()

    while True:
        user_text = input("You: ").strip()
        if not user_text:
            continue

        # quit
        if user_text.lower() in {"exit", "quit"}:
            print("Bye.")
            break

        # 2a. SQL path: use DataAgent directly
        if user_text.lower().startswith("sql:"):
            sql = user_text[4:].strip()
            if not sql:
                print("Please write a SELECT query after 'sql:'.")
                continue

            try:
                result = data_agent.run_sql_as_dicts(sql)
                print(f"\n[rows: {result['row_count']}] columns={result['columns']}")
                # show at most 10 rows in the CLI
                for row in result["rows"][:10]:
                    print(row)
                print()
            except Exception as e:
                print(f"SQL error: {e}")
            continue

        # 2b. Scoring path
        if user_text.lower().startswith("score:"):
            parts = user_text.split()
            country = parts[1].upper() if len(parts) > 1 else None
            top_n = 5
            if len(parts) > 2:
                try:
                    top_n = int(parts[2])
                except ValueError:
                    pass

            try:
                res = score_dealers(country=country, top_n=top_n)
                top = res.get("top_dealers", [])
                print(f"\nTop {len(top)} dealers:")
                for d in top:
                    print(
                        f"{d['dealer_id']} ({d['country']}) "
                        f"score={d['overall_score']:.1f} tier={d['tier']}"
                    )
                print()
            except Exception as e:
                print(f"Scoring error: {e}")
            continue

        # 2c. Recommendation path
        if user_text.lower().startswith("recommend:"):
            parts = user_text.split()
            country = parts[1].upper() if len(parts) > 1 else None

            try:
                res = recommend_dealer_actions(country=country, top_n=5)
                print("\nTop performers:")
                for d in res.get("top_performers", []):
                    print(f"- {d['dealer_id']} ({d['country']}): {d['message']}")
                print("\nAt risk dealers:")
                for d in res.get("at_risk_dealers", []):
                    print(f"- {d['dealer_id']} ({d['country']}): {d['message']}")
                print("\nGrowth opportunities:")
                for d in res.get("growth_opportunities", []):
                    print(f"- {d['dealer_id']} ({d['country']}): {d['message']}")
                print()
            except Exception as e:
                print(f"Recommendation error: {e}")
            continue

        # 3. Normal question: send through ADK to TinyLlama
        print("Bot:", end=" ", flush=True)
        last_text = ""
        async for event in runner.run_async(
            user_id=user_id,
            session_id=session.id,
            new_message=types.Content(
                role="user",
                parts=[types.Part(text=user_text)],
            ),
        ):
            if event.content and event.content.parts:
                # stream last chunk
                text = event.content.parts[0].text
                last_text = text
        # print final answer once
        if last_text:
            print(last_text)
        else:
            print("[no text output]")


if __name__ == "__main__":
    asyncio.run(main())
