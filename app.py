# app.py
from google.adk import App

from agents.dealer_copilot.agent import root_agent

# ADK will look for this symbol
app = App(
    agents=[root_agent],
)
