from google.adk import Agent
from google.adk.tools import google_search

root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash",
    description="Tool agent",
    instruction=(
        "You are a helpful assistant that can use the following tools "
        "to answer questions: google_search"
    ),
    tools=[google_search],
) 