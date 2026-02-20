import logging

from veadk import Agent, Runner
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.tools.builtin_tools.run_code import run_code

from agentkit.apps import AgentkitAgentServerApp

short_term_memory = ShortTermMemory(backend="local")


logger = logging.getLogger(__name__)

app_name = "agent_with_runcode"

agent: Agent = Agent(
    name="code_agent",
    model_name="deepseek-v3-2-251201",
    description="A fun Python coding assistant",
    instruction="You are a playful Python code experimenter. Your task is to leverage the sandbox environment to solve a variety of interesting problems. For example: simulating probability problems using the Monte Carlo method, generating fun ASCII art, or solving logic puzzles through algorithms. Please rely on the Python standard library as much as possible. You must use the run_code tool to execute your code and display the results to the user. Avoid installing complex external dependencies",
    tools=[run_code],
)

runner = Runner(agent=agent, app_name=app_name)
root_agent = agent

agent_server_app = AgentkitAgentServerApp(
    agent=agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    agent_server_app.run(host="0.0.0.0", port=8000)
