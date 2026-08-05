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

from veadk import Agent
from veadk.config import getenv
from veadk.tools.builtin_tools.web_search import web_search

from app.market.hook import hook_input_urls, hook_inline_data_transform
from app.market.prompt import PROMPT_MARKET_AGENT

from app.model import ArkLlm


def _web_search_enabled() -> bool:
    enable_web_search = os.getenv("ENABLE_WEB_SEARCH", "").lower()
    if enable_web_search in {"1", "true", "yes", "on"}:
        return True
    if enable_web_search in {"0", "false", "no", "off"}:
        return False

    return bool(
        (
            os.getenv("TOOL_WEB_SEARCH_ACCESS_KEY")
            and os.getenv("TOOL_WEB_SEARCH_SECRET_KEY")
        )
        or (os.getenv("VOLCENGINE_ACCESS_KEY") and os.getenv("VOLCENGINE_SECRET_KEY"))
    )


def get_market_agent():
    tools = [web_search] if _web_search_enabled() else []
    market_agent = Agent(
        name="market_agent",
        enable_responses=True,  # Enable responses to facilitate image understanding
        description="Based on the user's needs, generate the video configuration script",
        instruction=PROMPT_MARKET_AGENT,
        tools=tools,
        before_agent_callback=[hook_inline_data_transform],
        before_model_callback=[hook_input_urls],
        model_extra_config={
            "extra_body": {
                "thinking": {"type": getenv("THINKING_MARKET_AGENT", "disabled")},
                "caching": {
                    "type": "disabled",
                },
            }
        },
    )
    market_agent.model = ArkLlm(
        model=f"{market_agent.model_provider}/{market_agent.model_name}",
        api_key=market_agent.model_api_key,
        api_base=market_agent.model_api_base,
        **market_agent.model_extra_config,
    )
    return market_agent
