from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.redis import RedisSaver
from pydantic import BaseModel
from typing import TypedDict
from dotenv import load_dotenv

load_dotenv()

llm = ChatOpenAI()

def chat_node(state:MessagesState):
    """Invokes LLM to get a response based on user input"""

    messages = state['messages']
    response = llm.invoke(messages)

    return {'messages': [response]}

REDIS_URI = "redis://localhost:6379"

with RedisSaver.from_conn_string(REDIS_URI) as checkpointer:
    #only required once
    checkpointer.setup()

    builder = StateGraph(MessagesState)

    builder.add_node('chat_node', chat_node)

    builder.add_edge(START, 'chat_node')
    builder.add_edge('chat_node', END)

    chatbot = builder.compile(checkpointer=checkpointer)

