import streamlit as st
import requests
import os

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


# --- User Input Handling ---
if prompt := st.chat_input("질문을 입력하세요..."):
    # Add user message to chat chat history
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # --- Assistant Response Generation ---
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        message_placeholder.markdown("Thinking...")

        try:
            # Call the backend API
            response = requests.post(API_URL, json={"question": prompt})
            response.raise_for_status()  # Raise an exception for bad status codes
            
            data = response.json()
            assistant_response = data.get("answer", "죄송합니다, 답변을 생성하지 못했습니다.")
            thoughts = data.get("thoughts", [])

            # Display the final answer
            message_placeholder.markdown(assistant_response)

            # Store the full response including thoughts
            assistant_message = {
                "role": "assistant",
                "content": assistant_response,
                "thoughts": thoughts,
            }
            st.session_state.messages.append(assistant_message)

            # Display thoughts in an expander
            if thoughts:
                with st.expander("Agent's Thoughts"):
                    st.code("\n".join(thoughts), language="text")

        except requests.exceptions.RequestException as e:
            error_message = f"백엔드 API 호출에 실패했습니다: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
        except Exception as e:
            error_message = f"오류가 발생했습니다: {e}"
            message_placeholder.error(error_message)
            st.session_state.messages.append({"role": "assistant", "content": error_message})
