# Copyright (c) 2025 Beijing Volcano Engine Technology Co., Ltd. and/or its affiliates.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

from agentkit.apps import AgentkitAgentServerApp
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StreamableHTTPConnectionParams,
)
from prompts import SUPPORT_AGENT_PROMPT
from veadk import Agent, Runner
from veadk.knowledgebase.knowledgebase import KnowledgeBase
from veadk.memory.short_term_memory import ShortTermMemory
from veadk.memory.long_term_memory import LongTermMemory

kb = KnowledgeBase(
    backend="viking",
    app_name=os.getenv("DATABASE_VIKING_COLLECTION", "agentkit_knowledge_app"),
)

memory_collection_name = os.getenv("DATABASE_VIKINGMEM_COLLECTION")
if not memory_collection_name:
    raise ValueError("DATABASE_VIKINGMEM_COLLECTION environment variable is not set")

long_term_memory = LongTermMemory(backend="viking_mem", index=memory_collection_name)

instruction = SUPPORT_AGENT_PROMPT

mcp_url = os.getenv("MCP_TOOL_URL")
mcp_api_key = os.getenv("MCP_TOOL_API_KEY")
tools = []
if mcp_url and mcp_api_key:
    tools = [
        MCPToolset(
            connection_params=StreamableHTTPConnectionParams(
                url=mcp_url,
                headers={"Authorization": f"Bearer {mcp_api_key}"},
            )
        )
    ]

root_agent = Agent(
    name="rag_vikingdb_agent",
    knowledgebase=kb,
    tools=tools,
    instruction=instruction,
    long_term_memory=long_term_memory,
    auto_save_session=True
)

# runner = Runner(
#     agent=root_agent,
#     app_name="test_app",
#     user_id="test_user",
# )

short_term_memory = ShortTermMemory(backend="local")

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    agent_server_app.run(host="0.0.0.0", port=8000)
