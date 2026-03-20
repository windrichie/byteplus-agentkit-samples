import datetime
import os
import uuid
from zoneinfo import ZoneInfo

from agentkit.apps import AgentkitAgentServerApp
from google.adk.agents.callback_context import CallbackContext
from veadk import Agent
from veadk.agents.loop_agent import LoopAgent
from veadk.agents.sequential_agent import SequentialAgent
from veadk.memory.short_term_memory import ShortTermMemory

# Add current directory to Python path to support sub_agents imports
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from checker_agent import checker_agent_instance
from sub_agents.image import image_generation_agent
from sub_agents.prompt import image_generation_prompt_agent
from sub_agents.scoring import scoring_images_prompt


def set_session(callback_context: CallbackContext):
    """
    Sets a unique ID and timestamp in the callback context's state.
    This function is called before the main_loop_agent executes.
    """

    callback_context.state["unique_id"] = str(uuid.uuid4())
    callback_context.state["timestamp"] = datetime.datetime.now(
        ZoneInfo("UTC")
    ).isoformat()

# This agent is responsible for generating and scoring images based on input text.
# It uses a sequential process to:
# 1. Create an image generation prompt from the input text
# 2. Generate images using the prompt
# 3. Score the generated images
# The process continues until either:
# - The image score meets the quality threshold
# - The maximum number of iterations is reached
image_generation_scoring_agent = SequentialAgent(
    name="image_generation_scoring_agent",
    description=(
        """
        Analyzes a input text and creates the image generation prompt, generates the relevant images with Seedream and scores the images."
        1. Invoke the image_generation_prompt_agent agent to generate the prompt for generating images
        2. Invoke the image_generation_agent agent to generate the images
        3. Invoke the scoring_images_prompt agent to score the images
            """
    ),
    sub_agents=[
        image_generation_prompt_agent,
        image_generation_agent,
        scoring_images_prompt,
    ],
)

# --- 5. Define the Loop Agent ---
# The LoopAgent will repeatedly execute its sub_agents in the order they are listed.
# It will continue looping until one of its sub_agents (specifically, the checker_agent's tool)
# sets tool_context.actions.escalate = True.
image_scoring = LoopAgent(
    name="image_scoring",
    description="Repeatedly runs a sequential process and checks a termination condition.",
    sub_agents=[
        image_generation_scoring_agent, # First, run your sequential process [1]
        checker_agent_instance, # Second, check the condition and potentially stop the loop [1]
    ],
    before_agent_callback=set_session
)

root_agent = image_scoring

short_term_memory = ShortTermMemory(backend="local")
root_agent.short_term_memory = short_term_memory

if __name__ == "__main__":
    agent_server_app = AgentkitAgentServerApp(
        agent=root_agent,
        short_term_memory=short_term_memory,
    )
    port = int(os.getenv("PORT", "8000"))
    agent_server_app.run(host="0.0.0.0", port=port)
