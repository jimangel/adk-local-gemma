import os
from google.adk import Agent
from google.adk.tools import google_search

MODEL = os.getenv('GEMINI_MODEL', 'gemini-2.5-pro')

google_search_agent = Agent(
    model=MODEL,
    name="google_search_agent",
    instruction="search google if needed",
    output_key="google_search_output",
    tools=[google_search],
)