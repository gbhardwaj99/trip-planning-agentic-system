from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import BaseModel
from typing import TypedDict
from dotenv import load_dotenv
import time

load_dotenv()

llm = ChatOpenAI()

def chat_node(state:MessagesState):
    """Invokes LLM to get a response based on user input"""

    messages = state['messages']
    response = llm.invoke(messages)

    return {'messages': [response]}

def search_node(state:MessagesState):
    """Dummy search node to send server events for searching"""
    time.sleep(5)
    return {}

def call_tools(state:MessagesState):
    """Dummy tool node to send server events for tool calls"""
    time.sleep(5)
    return {}


builder = StateGraph(MessagesState)

builder.add_node('chat_node', chat_node)
builder.add_node('search_node', search_node)
builder.add_node('call_tools', call_tools)

builder.add_edge(START, 'search_node')
builder.add_edge('search_node', 'call_tools')
builder.add_edge('call_tools', 'chat_node')
builder.add_edge('chat_node', END)

checkpointer = InMemorySaver()

chatbot = builder.compile(checkpointer=checkpointer)

