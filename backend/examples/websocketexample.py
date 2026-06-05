from fastapi import FastAPI, WebSocket, Depends, Cookie, Query, WebSocketException, status
from fastapi.responses import HTMLResponse
from typing import Annotated
from langgraph_backend import chatbot

app = FastAPI()

html = """
<!DOCTYPE html>
<html>
    <head>
        <title>Chat</title>
    </head>
    <body>
        <h1>WebSocket Chat</h1>
        <form action="" onsubmit="sendMessage(event)">
            <label>Thread ID: <input type="text" id="threadId" autocomplete="off" value="foo"/></label>
            <label>Token: <input type="text" id="token" autocomplete="off" value="some-key-token"/></label>
            <button onclick="connect(event)">Connect</button>
            <hr>
            <label>Message: <input type="text" id="messageText" autocomplete="off"/></label>
            <button>Send</button>
        </form>
        <ul id="messages">
        </ul>
        <script>
            var ws = null;
            print("I was here")
            function connect(event) {
                var thread_id = document.getElementById("threadId")
                var token = document.getElementById("token")
                ws = new WebSocket("ws://localhost:8000/ws/" + thread_id.value + "?token=" + token.value)
                ws.onmessage = function(event) {
                    var messages = document.getElementById('messages')
                    var message = document.createElement('li')
                    var content = document.createTextNode(event.data)
                    message.appendChild(content)
                    messages.appendChild(message)
                }
                event.preventDefault()
            }
            
            function sendMessage(event) {
                var input = document.getElementById("messageText")
                ws.send(input.value)
                input.value = ''
                event.preventDefault()
            }
        </script>
    </body>
</html>
"""

@app.get("/")
async def get():
    return HTMLResponse(html)

async def get_cookie_or_token(
    websocket: WebSocket,
    session: Annotated[str | None, Cookie()] = None,
    token: Annotated[str | None, Query()] = None
):
    if session is None and token is None:
        raise WebSocketException(code=status.WS_1008_POLICY_VIOLATION)
    return session or token

@app.websocket("/ws/{thread_id}")
async def websocket_endpoint(
    *,
    websocket: WebSocket,
    thread_id: str,
    q: int | None = None,
    cookie_or_token: Annotated[str, Depends(get_cookie_or_token)]
):
    await websocket.accept()
    print("Client connected!")
    await websocket.send_text(
        f"Session cookie or query token is: {cookie_or_token}"
    )
    while True:
        data = await websocket.receive_text()
        await websocket.send_text(
            f"Human: {data}"
        )

        response = await chatbot.ainvoke(
            {"messages": {"role":"user", "content":data}},
            config={"configurable":{"thread_id":thread_id}}
        )
        ai_response = response["messages"][-1].content

        if q is not None:
            await websocket.send_text(f"Query parameter q is: {q}")

        await websocket.send_text(f"AI: {ai_response}")