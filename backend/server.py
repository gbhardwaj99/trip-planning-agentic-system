from fastapi import FastAPI, HTTPException, WebSocket, Depends, Cookie, Query, WebSocketException, status, WebSocketDisconnect
from fastapi.responses import JSONResponse
from langgraph_backend import builder_graph
from database.thread_db import ChatDatabase
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.redis import AsyncRedisSaver
from typing import Annotated
from contextlib import asynccontextmanager
from pydantic import BaseModel

class ThreadRequest(BaseModel):
    thread_id: str

REDIS_URI = "redis://localhost:6379"

@asynccontextmanager
async def lifespan(app:FastAPI):
    checkpointer_cm = AsyncRedisSaver.from_conn_string(REDIS_URI)

    checkpointer = await checkpointer_cm.__aenter__()

    await checkpointer.setup()

    app.state.chatbot = await builder_graph(checkpointer=checkpointer)

    db = ChatDatabase()

    app.state.db = db

    yield

    await checkpointer_cm.__aexit__(None, None, None)

app = FastAPI(lifespan=lifespan)

async def get_cookie_or_token(
    websocket: WebSocket,
    session: Annotated[str | None, Cookie()] = None,
    token: Annotated[str | None, Query()] = None
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token

@app.get("/")
def welcome_page():
    return {"message": "Trip Planning Workflow Api Endpoint"}

@app.get("/history/{thread_id}")
def get_chat_history(thread_id):
    config = {"configurable": {"thread_id": thread_id}}
    state = app.state.chatbot.get_state(config=config)
    return state.values.get("messages", [])

@app.get("/threadhistory")
def get_thread_history():
    try:
        threads = app.state.db.get_threads()
        return {"threads": threads}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.post("/thread")
def save_thread(payload: ThreadRequest):
    try:
        app.state.db.save_thread(payload.thread_id)
        return {"message": "thread added successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.websocket("/ws/chat/{thread_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    thread_id: str,
    # cookie_or_token: Annotated[str, Depends(get_cookie_or_token)]
):
    await websocket.accept()
    print(f"Client connected with Thread ID: {thread_id}")

    try:
        while True:
            user_input = await websocket.receive_text()
            
            async for event in app.state.chatbot.astream_events(
                {"messages": [HumanMessage(content=user_input)]},
                config={"configurable":{"thread_id":thread_id}},
                version="v2"
            ):
                kind = event["event"]
                name = event.get("name", "")

                # Catch when a graph node, tool, or model begins executing.
                if kind == "on_chain_start":
                    status_text = f"Status: Entering node '{name}' 🔎..."
                    if name == "call_tools":
                        status_text = "Status: Executing tool pipelines 🛠️..."

                    await websocket.send_json({"type": "status", "content": status_text})

                elif kind == "on_tool_start":
                    await websocket.send_json({"type": "status", "content": f"Status: Running tool '{name}' 🔧..."})

                elif kind == "on_chat_model_start":
                    await websocket.send_json({"type": "status", "content": f"Status: Generating response from '{name}'..."})

                # Catch raw token chunks streaming from the LLM
                elif kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and chunk.content:
                        await websocket.send_json({"type": "token", "content": chunk.content})
                

            await websocket.send_json({"type": "terminate", "content": ""})

    except WebSocketDisconnect:
        print(f"Client disconnected gracefully: {thread_id}")
    
    except Exception as e:
        print(f"Error in Websocket session: {e}")
        try:
            await websocket.close()
        except:
            pass
