from google.adk import Agent

root_agent = Agent(
    name="root_agent",
    model="gemini-2.0-flash",
    description="Greeting agent",
    instruction=(
        "You are a helpful assistant that can greet the user. "
        "Ask the user's name and greet them by name."
    ),
)