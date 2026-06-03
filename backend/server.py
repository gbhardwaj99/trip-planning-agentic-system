from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.responses import JSONResponse
from langgraph_backend import graph

app = FastAPI()

@app.get("/chat")
async def handle_chat(query: str):

    request = " ".join(query.split("%"))

    config = {"configurable": {"thread_id": "thread-1"}}
    print("got here-1")
    try:
        print("got here-2")
        response = await graph.ainvoke({"messages": {"role":"user", "content":request}}, config=config)
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading LLM workflow")

    return JSONResponse(status_code=200, content={'response': response})

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    print("hello world")