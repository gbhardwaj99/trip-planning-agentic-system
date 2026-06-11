from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import BaseTool
from langgraph.prebuilt import ToolNode, tools_condition
from pydantic import BaseModel
from typing import TypedDict
from dotenv import load_dotenv
import time
import asyncio
import threading

load_dotenv()

# Dedicated async loop for backend tasks
_ASYNC_LOOP = asyncio.new_event_loop()
_ASYNC_THREAD = threading.Thread(target=_ASYNC_LOOP.run_forever, daemon=True)
_ASYNC_THREAD.start()

# -------------------
# 1. To run backend synchronous tasks asynchronously
# -------------------

def _submit_async(coro):
    return asyncio.run_coroutine_threadsafe(coro, _ASYNC_LOOP)

def run_async(coro):
    return _submit_async(coro).result()

def submit_async_task(coro):
    """Schedule a coroutine on the backend event loop."""
    return _submit_async(coro)

llm = ChatOpenAI()

client = MultiServerMCPClient(
    {
        "tripplanning": {
            "transport": "stdio",
            "command": "python",
            "args": ["C:\\Users\\g.chetan.bhardwaj\\Documents\\Learn\\trip_planning_chatbot\\mcp\\main.py"]
        }
    }
)

search_tool = DuckDuckGoSearchRun()

def load_mcp_tools() -> list[BaseTool]:
    try:
        tools = run_async(client.get_tools())
        print("Loaded MCP tools:", [t.name for t in tools])
        return tools

    except Exception as e:
        import traceback
        traceback.print_exc()
        print("MCP ERROR:", e)
        raise

mcp_tools = load_mcp_tools()

tools = [search_tool, *mcp_tools]

llm_with_tools = llm.bind_tools(tools) if tools else llm

async def builder_graph(checkpointer):

    def chat_node(state:MessagesState):
        """Invokes LLM to get a response based on user input"""

        messages = state['messages']
        response = llm.invoke(messages)

        return {'messages': [response]}

    tool_node = ToolNode(tools) if tools else None

    builder = StateGraph(MessagesState)

    builder.add_node('chat_node', chat_node)
    builder.add_edge(START, 'chat_node')

    if tool_node:
        builder.add('tools', tool_node)
        builder.add_conditional_edges('chat_node', tools_condition)
        builder.add_edge('tools', 'chat_node')
    else:
        builder.add_edge('chat_node', END)

    chatbot = builder.compile(checkpointer=checkpointer)

    return chatbot

