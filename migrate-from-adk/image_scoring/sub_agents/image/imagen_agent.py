from veadk import Agent


import config
from sub_agents.image.prompt import IMAGEGEN_PROMPT
from sub_agents.image.tools.image_generation_tool import generate_images

image_generation_agent = Agent(
    name="image_generation_agent",
    model_name=config.MODEL_AGENT_NAME,
    description="You are an expert in creating images with Seedream",
    instruction=IMAGEGEN_PROMPT,
    tools=[generate_images],
    output_key="output_image",
)
