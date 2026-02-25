import asyncio

from google.adk.tools.tool_context import ToolContext
from prompts import (
    JUDGE_AGENT_PROMPT,
    LOOP_REFINE_RESPONSE_AGENT_PROMPT,
    REFINE_AGENT_PROMPT,
)
from veadk import Agent, Runner
from veadk.agents.loop_agent import LoopAgent
from veadk.memory.short_term_memory import ShortTermMemory

judge_agent = Agent(
    name="judge_agent",
    description="Evaluates the customer-support reply (no rewriting) and provides verdict, reasons, and improvement directions.",
    instruction=JUDGE_AGENT_PROMPT,
)

refine_agent = Agent(
    name="refine_agent",
    description="Rewrites the reply based on judge_agent feedback to meet both usefulness and politeness requirements.",
    instruction=REFINE_AGENT_PROMPT,
)


def exit_tool(tool_context: ToolContext) -> str:
    print(f"  [Tool Call] exit_loop triggered by {tool_context.agent_name}")
    # tool_context.actions.escalate = True
    tool_context.actions.end_of_agent = True
    return {}


loop_refine_response_agent = LoopAgent(
    name="loop_refine_response_agent",
    description="Coordinates reply evaluation and rewriting, and outputs the final optimized response.",
    instruction=LOOP_REFINE_RESPONSE_AGENT_PROMPT,
    sub_agents=[judge_agent, refine_agent],
    tools=[exit_tool],
    max_iterations=1,
)


app_name = "veadk_playground_app"
user_id = "veadk_playground_user"
session_id = "veadk_playground_session"

short_term_memory = ShortTermMemory()

runner = Runner(
    agent=loop_refine_response_agent,
    short_term_memory=short_term_memory,
    app_name=app_name,
    user_id=user_id,
)


async def main():
    response = await runner.run(
        messages='User question: "The clothing size I bought runs small. Can I exchange for a larger size? What is the process?" Original support reply: "Yes. Keep the tags and ship it back yourself. Pay shipping first and we will reimburse you later."',
        session_id=session_id,
    )
    print(response)


if __name__ == "__main__":
    asyncio.run(main())
