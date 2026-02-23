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


from agentkit.apps import AgentkitAgentServerApp
from veadk import Agent, Runner
from veadk.knowledgebase.knowledgebase import KnowledgeBase
from veadk.memory.short_term_memory import ShortTermMemory
import os

kb = KnowledgeBase(
    backend="viking",
    app_name=os.getenv("DATABASE_VIKING_COLLECTION", "agentkit_knowledge_app"),
)

# Create agent
root_agent = Agent(
    name="rag_vikingdb_agent",
    knowledgebase=kb,
    instruction="You are a helpful customer support assistant. Use the knowledge base to answer questions about product categories, pricing, and after-sales policies. Answer accurately based on the knowledge base content.",
)

# Run
runner = Runner(
    agent=root_agent,
    app_name="test_app",
    user_id="test_user",
)

short_term_memory = ShortTermMemory(backend="local")

agent_server_app = AgentkitAgentServerApp(
    agent=root_agent,
    short_term_memory=short_term_memory,
)

if __name__ == "__main__":
    agent_server_app.run(host="0.0.0.0", port=8000)
