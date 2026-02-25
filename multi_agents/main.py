import asyncio

from multi_agents.agent import root_agent
from veadk import Runner
from veadk.memory.short_term_memory import ShortTermMemory

app_name = "veadk_playground_app"
user_id = "veadk_playground_user"
session_id = "veadk_playground_session"

short_term_memory = ShortTermMemory()

runner = Runner(
    agent=root_agent,
    short_term_memory=short_term_memory,
    app_name=app_name,
    user_id=user_id,
)


async def main():
    response = await runner.run(
        messages="I want to buy a cloud VM for image processing. Which instance type would you recommend?",
        session_id=session_id,
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
