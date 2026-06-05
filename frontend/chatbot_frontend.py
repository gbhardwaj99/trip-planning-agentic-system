import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh
from langchain_core.messages import HumanMessage
from fastapi import WebSocket
import asyncio
import websockets
import threading
import queue
import requests
import uuid
import json

# st_autorefresh(interval=500, key="websocket_ui_cleaner")

st.set_page_config(layout="wide", page_title="Streamlit Websocket Client")
st.title("Trip planning chatbot")

#---------------------------------------------------------#
#                   UTILITY FUNCTIONS                   
#---------------------------------------------------------#

def generate_thread():
    new_thread_id = uuid.uuid4()
    return new_thread_id

def get_chat(thread_id):
    response = requests.get(f"http://127.0.0.1:8000/history/{thread_id}")
    result = response.json()
    return [{"role": message["type"], "content": message["content"]} for message in result]

def add_thread(thread_id):
    if thread_id not in st.session_state.chat_threads:
        st.session_state.chat_threads.append(thread_id)

#---------------------------------------------------------#
#                   SESSION MANAGEMENT                   
#---------------------------------------------------------#

params = st.query_params

if "out_queue" not in st.session_state:
    st.session_state.out_queue = queue.Queue(maxsize=2000)

if "in_queue" not in st.session_state:
    st.session_state.in_queue = queue.Queue()

if "chat_threads" not in st.session_state:
    st.session_state.chat_threads = []

if "current_thread" not in st.session_state:
    if "thread_id" in params:
        st.session_state.current_thread = params["thread_id"]
    else:
        new_thread_id = generate_thread()
        params["thread_id"] = new_thread_id
        st.session_state.current_thread = new_thread_id
    add_thread(st.session_state.current_thread)

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
    for message in get_chat(st.session_state.current_thread):
        st.session_state.chat_history.append({
            "role": "user" if message["type"] == "human" else "ai",
            "content": message["content"]
        })


def queue_stream():
    while True:
        token = st.session_state.in_queue.get()

        if token["type"] == "terminate":
            break

        yield token

#---------------------------------------------------------#
#                   WEBSOCKET WORKERS                     
#---------------------------------------------------------#

async def websocket_worker(uri, out_queue, in_queue):
    """Maintains a single persistent connection to FastAPI."""
    async with websockets.connect(uri) as websocket:
        while True:
            #Check for outbound messages to send
            try:
                msg_to_send = out_queue.get_nowait()
                if msg_to_send == "WS_STOP":
                    try:
                        await websocket.close()
                    except Exception:
                        pass
                    break
                else:
                    await websocket.send(msg_to_send)
            except queue.Empty:
                pass

            #Listen for inbound messages from FastAPI
            try:
                # set a short timeout so the loop stays responsive to outbound queue
                response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                in_queue.put(json.loads(response))
                
            except asyncio.TimeoutError:
                pass
            except Exception:
                break
            await asyncio.sleep(0.01)

def start_websocket_thread(thread_id, oq, iq):
    """Starts the async worker loop inside a persistent background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(
        websocket_worker(f"ws://localhost:8000/ws/chat/{thread_id}", oq, iq)
    )

def start_new_ws_thread(thread_id):
    # Signal existing worker (if any) to stop and wait briefly
    if "ws_thread" in st.session_state and st.session_state.ws_thread is not None:
        try:
            st.session_state.out_queue.put("WS_STOP")
        except Exception:
            pass

        try:
            st.session_state.ws_thread.join(timeout=2)
        except Exception:
            pass

    # create fresh per-connection queues
    st.session_state.out_queue = queue.Queue(maxsize=2000)
    st.session_state.in_queue = queue.Queue()

    thread = threading.Thread(
        target=start_websocket_thread,
        args=(thread_id, st.session_state.out_queue, st.session_state.in_queue),
        daemon=True
    )

    # attach the streamlit runtime session context to it
    add_script_run_ctx(thread)

    st.session_state.ws_thread = thread
    st.session_state.ws_thread.start()


if "ws_thread" not in st.session_state:
    start_new_ws_thread(st.session_state.current_thread)

#---------------------------------------------------------#
#                   MAIN UI                     
#---------------------------------------------------------#

with st.sidebar:
    
    if st.button("New Chat"):
        new_thread_id = generate_thread()
        st.session_state.current_thread = new_thread_id
        start_new_ws_thread(st.session_state.current_thread)
        
        st.session_state.chat_history = []
        params["thread_id"] = new_thread_id
        add_thread(new_thread_id)
        st.rerun()
        
    st.header("My Conversations")

    for thread in st.session_state.chat_threads:
        if st.button(str(thread)):
            params["thread_id"] = thread
            st.session_state.current_thread = thread
            start_new_ws_thread(st.session_state.current_thread)

            st.session_state.chat_history = get_chat(thread)
            st.rerun()

user_input = st.chat_input("Your message!")

if st.session_state.chat_history:
    for message in st.session_state.chat_history:
        with st.chat_message(message["role"]):
            st.write(message["content"])

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.chat_history.append({"role":"user", "content":user_input})
    
    st.session_state.out_queue.put(user_input)
    st.toast("Message queued for sending!")

    status_placeholder = st.empty()
    ai_response = ""

    with status_placeholder.container():
        status_box = st.status("Initializing agent workflow...", expanded=True)
        ai_message = st.chat_message("ai")
        token_placeholder = ai_message.empty()

        for token in queue_stream():
            if token["type"] == "status":
                status_box.update(label=token["content"], state="running")

            elif token["type"] == "token":
                ai_response += token["content"]
                token_placeholder.markdown(ai_response)

        status_box.update(label="Complete", state="complete")

    st.session_state.chat_history.append({
        "role": "ai",
        "content": ai_response
    })

    st.rerun()
