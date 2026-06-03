import streamlit as st
from streamlit.runtime.scriptrunner import add_script_run_ctx
from streamlit_autorefresh import st_autorefresh
from fastapi import WebSocket
import asyncio
import websockets
import threading
import queue

# st_autorefresh(interval=500, key="websocket_ui_cleaner")

st.set_page_config(layout="wide", page_title="Streamlit Websocket Client")
st.title("Trip planning chatbot")

if "out_queue" not in st.session_state:
    st.session_state.out_queue = queue.Queue(maxsize=2000)

if "in_queue" not in st.session_state:
    st.session_state.in_queue = queue.Queue()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

def queue_stream():
    while True:
        token = st.session_state.in_queue.get()

        if token == "__END__":
            break

        yield token

async def websocket_worker(uri, out_queue, in_queue):
    """Maintains a single persistent connection to FastAPI."""
    async with websockets.connect(uri) as websocket:
        while True:
            #Check for outbound messages to send
            try:
                msg_to_send = out_queue.get_nowait()
                await websocket.send(msg_to_send)
            except queue.Empty:
                pass

            #Listen for inbound messages from FastAPI
            try:
                # set a short timeout so the loop stays responsive to outbound queue
                response = await asyncio.wait_for(websocket.recv(), timeout=0.1)
                in_queue.put(response)
                
            except asyncio.TimeoutError:
                pass
            except Exception:
                break
            await asyncio.sleep(0.01)

def start_websocket_thread(oq, iq):
    """Starts the async worker loop inside a persistent background thread"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(websocket_worker("ws://localhost:8000/ws/chat/thread-1", oq, iq))

if "ws_thread" not in st.session_state:
    thread = threading.Thread(
        target=start_websocket_thread,
        args=(st.session_state.out_queue, st.session_state.in_queue),
        daemon=True
    )

    # attach the streamlit runtime session context to it
    add_script_run_ctx(thread)

    st.session_state.ws_thread = thread
    st.session_state.ws_thread.start()

with st.sidebar:
    
    if st.button("Connect"):
        st.write("Client connected!")

user_input = st.chat_input("Your message!")

for message in st.session_state.chat_history:
    with st.chat_message(message["role"]):
        st.write(message["content"])

if user_input:
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.chat_history.append({"role":"user", "content":user_input})
    
    st.session_state.out_queue.put(user_input)
    st.toast("Message queued for sending!")

    with st.chat_message("ai"):
        ai_message = st.write_stream(queue_stream())

    st.session_state.chat_history.append({
        "role": "ai",
        "content": ai_message
    })

    st.rerun()
