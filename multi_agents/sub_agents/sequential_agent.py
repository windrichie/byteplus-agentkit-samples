import asyncio

from prompts import PRE_PROCESS_AGENT_PROMPT, SEQUENTIAL_SERVICE_AGENT_PROMPT
from sub_agents.loop_agent import loop_refine_response_agent
from sub_agents.parallel_agent import parallel_get_info_agent
from veadk import Agent, Runner
from veadk.agents.sequential_agent import SequentialAgent
from veadk.memory.short_term_memory import ShortTermMemory


pre_process_agent = Agent(
    name="pre_process_agent",
    description="A requirements analyst that classifies the request and extracts key details for downstream agents.",
    instruction=PRE_PROCESS_AGENT_PROMPT,
)

sequential_service_agent = SequentialAgent(
    name="sequential_service_agent",
    description="Runs the workflow step-by-step and produces the best final reply.",
    instruction=SEQUENTIAL_SERVICE_AGENT_PROMPT,
    sub_agents=[pre_process_agent, parallel_get_info_agent, loop_refine_response_agent],
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
        messages="I bought a cloud VM for image processing, but the performance doesn't meet my needs. Please analyze why and recommend a better instance type if needed.",
        session_id=session_id,
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
