from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from langgraph_backend import graph
from langchain_core.messages import HumanMessage

app = FastAPI()

@app.get("/chat")
async def handle_chat(query: str):
    try:
        response = graph.ainvoke(HumanMessage(content=query))
    except Exception as e:
        raise HTTPException(status_code=500, detail="Error loading LLM workflow")

    return JSONResponse(status_code=200, content={'message': response.content})

