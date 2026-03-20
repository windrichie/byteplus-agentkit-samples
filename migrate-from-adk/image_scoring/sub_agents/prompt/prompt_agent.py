from veadk import Agent


import config
from sub_agents.tools.fetch_policy_tool import get_policy
from sub_agents.prompt.prompt import PROMPT

image_generation_prompt_agent = Agent(
    name="image_generation_prompt_agent",
    model_name=config.MODEL_AGENT_NAME,
    description="You are an expert in creating Seedream prompts for image generation",
    instruction=PROMPT,
    tools=[get_policy],
    output_key="imagen_prompt", # gets stored in session.state
)
