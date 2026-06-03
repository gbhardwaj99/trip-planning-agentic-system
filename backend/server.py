from fastapi import FastAPI, HTTPException, WebSocket, Depends, Cookie, Query, WebSocketException, status, WebSocketDisconnect
from fastapi.responses import JSONResponse
from langgraph_backend import chatbot
from typing import Annotated

app = FastAPI()

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
            
            async for message_chunk, metadata in chatbot.astream(
                {"messages": {"role":"user", "content":user_input}},
                config={"configurable":{"thread_id":thread_id}},
                stream_mode="messages"
            ):
                await websocket.send_text(message_chunk.content)

            await websocket.send_text("__END__")

    except WebSocketDisconnect:
        print(f"Client disconnected gracefully: {thread_id}")
    
    except Exception as e:
        print(f"Error in Websocket session: {e}")
        try:
            await websocket.close()
        except:
            pass
