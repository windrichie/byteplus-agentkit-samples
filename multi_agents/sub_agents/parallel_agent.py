import asyncio

from prompts import (
    PARALLEL_GET_INFO_AGENT_PROMPT,
    RAG_SEARCH_AGENT_PROMPT,
    WEB_SEARCH_AGENT_PROMPT,
)
from veadk import Agent, Runner
from veadk.agents.parallel_agent import ParallelAgent
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.tools.builtin_tools.web_search import web_search

rag_search_agent = Agent(
    name="rag_search_agent",
    description="Retrieves relevant information from the built-in knowledge base.",
    instruction=RAG_SEARCH_AGENT_PROMPT,
)

web_search_agent = Agent(
    name="web_search_agent",
    description="Searches the web for up-to-date information related to the user's question.",
    instruction=WEB_SEARCH_AGENT_PROMPT,
    tools=[web_search],
)

parallel_get_info_agent = ParallelAgent(
    name="parallel_get_info_agent",
    description="Runs sub-tasks in parallel to quickly gather relevant information.",
    instruction=PARALLEL_GET_INFO_AGENT_PROMPT,
    # enable web_search_agent if you want to observe how two parallel agents work
    # sub_agents=[rag_search_agent, web_search_agent],
    sub_agents=[rag_search_agent],
)


app_name = "veadk_playground_app"
user_id = "veadk_playground_user"
session_id = "veadk_playground_session"

short_term_memory = ShortTermMemory()

runner = Runner(
    agent=parallel_get_info_agent,
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
