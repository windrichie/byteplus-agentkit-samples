import asyncio
from google.adk.tools import ToolContext

ctx = ToolContext()
ctx.actions.escalate = True
print("escalate is set to:", ctx.actions.escalate)

