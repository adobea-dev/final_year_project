root_agent = Agent(
    name = "dealer_copilot",
    model = "ollama : tinyllama",
    description = "Root orchestrator for dealer insights and recommendations.",
    instruction = """ 
    You manage scorin, recommendations, data retrieval, and visualizations.
    When needed:
    - use the scoring_agent to score dealers
    - use the data_agent to fetch data from postgres, csv, api, duckdb
    - use the visualization_agent to generate charts
    - use the recommendation_agent to suggest actions
    """,
)
 #the brain , main orchestrator 