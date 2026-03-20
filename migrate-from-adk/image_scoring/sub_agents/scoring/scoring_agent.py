from veadk import Agent


import config
from sub_agents.tools.fetch_policy_tool import get_policy
from sub_agents.scoring.prompt import SCORING_PROMPT
from sub_agents.scoring.tools.get_images_tool import get_image
from sub_agents.scoring.tools.set_score_tool import set_score

scoring_images_prompt = Agent(
    name="scoring_images_prompt",
    model_name=config.MODEL_AGENT_NAME,
    description=(
        "You are an expert in evaluating and scoring images based on various criteria "
        "provided to you."
    ),
    instruction=SCORING_PROMPT,
    output_key="scoring",
    tools=[get_policy, get_image, set_score],
)
