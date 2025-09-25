import streamlit as st
import requests
import os
import json
import logging

# Configure logger
logger = logging.getLogger(__name__)

# --- App Configuration ---
st.set_page_config(page_title="Text-to-SQL Chatbot", page_icon="💬")
st.title("💬 Text-to-SQL Chatbot")

# --- Backend API Configuration ---
# It's better to use an environment variable for the API URL
API_URL = os.getenv("API_URL", "http://127.0.0.1:8000/agent/invoke")

# --- Session State Initialization ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {
            "role": "assistant",
            "content": "안녕하세요! 데이터에 대해 궁금한 점을 질문해주세요. 제가 SQL 쿼리를 생성하여 답변해 드립니다.",
        }
    ]

# --- Chat History Display ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])
        # Display thoughts if they exist
        if "thoughts" in message and message["thoughts"]:
            with st.expander("Agent's Thoughts"):
                st.code("\n".join(message["thoughts"]), language="text")


if prompt := st.chat_input("질문을 입력하세요..."):
    # Add user message to chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Assistant Response Generation ---
    with st.chat_message("assistant"):
        thoughts_expander = st.expander("Agent's Thoughts")
        thoughts_container = thoughts_expander.empty()
        message_placeholder = st.empty()
        
        all_thoughts = []
        full_response = ""

        try:
            with requests.post(API_URL, json={"question": prompt}, stream=True) as response:
                response.raise_for_status()
                for line in response.iter_lines():
                    if line:
                        decoded_line = line.decode('utf-8')
                        if decoded_line.startswith('data: '):
                            try:
                                event_data = json.loads(decoded_line[6:])
                                event_type = event_data.get("type")
                                data = event_data.get("data")

                                if event_type == "thought":
                                    all_thoughts.append(data)
                                    thoughts_container.code("\n".join(all_thoughts), language="text")
                                
                                elif event_type == "answer":
                                    full_response = data
                                    message_placeholder.markdown(full_response)

                                elif event_type == "error":
                                    full_response = f"Error: {data}"
                                    st.error(full_response)
                                    break

                            except json.JSONDecodeError:
                                logger.warning(f"Could not decode JSON from stream: {decoded_line}")

            # Store the full response in session state after the stream is complete
            assistant_message = {
                "role": "assistant",
                "content": full_response,
                "thoughts": all_thoughts,
            }
            st.session_state.messages.append(assistant_message)

        except requests.exceptions.RequestException as e:
            error_message = f"백엔드 API 호출에 실패했습니다: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        except Exception as e:
            error_message = f"오류가 발생했습니다: {e}"
            st.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
