import os
from agentkit.apps import AgentkitAgentServerApp
from veadk import Agent
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.tools.builtin_tools.image_generate import image_generate
from veadk.tools.builtin_tools.video_generate import video_generate


root_agent = Agent( 
    name="quick_video_create_agent",
    description=("You are an expert in creating images and video"),
    instruction="""You can create images and using the images to generate video.""",
    tools=[image_generate, video_generate],
)

agent = root_agent

short_term_memory = ShortTermMemory(backend="local")

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    agent_server_app.run(host="0.0.0.0", port=port)
