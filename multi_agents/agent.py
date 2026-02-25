import os
import sys

from agentkit.apps import AgentkitAgentServerApp
from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory


# Add current directory to Python path to support sub_agents imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prompts import CUSTOMER_SERVICE_AGENT_PROMPT
from sub_agents.sequential_agent import sequential_service_agent

short_term_memory = ShortTermMemory(
    backend="local"
)  # Use local backend for ShortTermMemory()

customer_service_agent = Agent(
    name="customer_service_agent",
    description="Xiaoxing, the Stellar Commerce customer-support agent for orders, shipping, after-sales, and membership inquiries.",
    instruction=CUSTOMER_SERVICE_AGENT_PROMPT,
    sub_agents=[sequential_service_agent],
)

root_agent = customer_service_agent

runner = Runner(agent=root_agent)

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    agent_server_app.run(host="0.0.0.0", port=port)
