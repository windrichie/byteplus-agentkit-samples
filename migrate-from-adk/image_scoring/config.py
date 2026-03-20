import os

SCORE_THRESHOLD = int(os.getenv("SCORE_THRESHOLD", "45"))
MAX_ITERATIONS = int(os.getenv("MAX_ITERATIONS", "1"))

MODEL_AGENT_NAME = os.getenv("MODEL_AGENT_NAME", "deepseek-v3-2-251201")
MODEL_AGENT_API_BASE = os.getenv(
    "MODEL_AGENT_API_BASE", "https://ark.ap-southeast.byteplus.com/api/v3/"
)
MODEL_AGENT_API_KEY = os.getenv("MODEL_AGENT_API_KEY")

IMAGE_TASK_TYPE = os.getenv("IMAGE_TASK_TYPE", "text_to_single")
IMAGE_SIZE = os.getenv("IMAGE_SIZE", "1440x2560")
IMAGE_MODEL_NAME = os.getenv("MODEL_IMAGE_NAME")
