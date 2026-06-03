from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, START, END
from langgraph.graph.message import MessagesState
from langgraph.checkpoint.memory import InMemorySaver
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

builder = StateGraph(MessagesState)

checkpointer = InMemorySaver()

builder.add_node('chat_node', chat_node)

builder.add_edge(START, 'chat_node')
builder.add_edge('chat_node', END)

graph = builder.compile(checkpointer=checkpointer)