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

from app.release.hook import hook_tool_execute
from app.release.prompt import PROMPT_RELEASE_AGENT
from app.release.tools.video_combine import video_combine_and_upload
from app.model import ArkLlm


def get_release_agent() -> Agent:
    agent = Agent(
        name="release_agent",
        description="Compose the storyboard videos into the final video",
        instruction=PROMPT_RELEASE_AGENT,
        tools=[video_combine_and_upload],
        after_tool_callback=[hook_tool_execute],
        model_extra_config={
            "extra_body": {
                "thinking": {"type": os.getenv("THINKING_RELEASE_AGENT", "disabled")},
                "caching": {
                    "type": "disabled",
                },
            }
        },
    )

    agent.model = ArkLlm(
        model=f"{agent.model_provider}/{agent.model_name}",
        api_key=agent.model_api_key,
        api_base=agent.model_api_base,
        **agent.model_extra_config,
    )
    return agent
