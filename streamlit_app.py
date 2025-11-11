import streamlit as st
import requests

st.title("Ollama -> TTS Demo")

# The URL for our FastAPI chatbot endpoint
CHATBOT_URL = "http://127.0.0.1:8080/chatbot/audio-response"

# Text input for the user's prompt
prompt = st.text_input("Enter your prompt for the AI:")

if st.button("Generate Audio"):
    if prompt:
        try:
            with st.spinner("Generating response and audio..."):
                # 1. Send the prompt to the chatbot endpoint
                payload = {"prompt": prompt}
                response = requests.post(CHATBOT_URL, json=payload)
                response.raise_for_status()

                # 2. The response content is the audio bytes
                audio_bytes = response.content
                
                # 3. Display the audio player in Streamlit
                st.audio(audio_bytes, format="audio/mpeg")

        except requests.exceptions.RequestException as e:
            st.error(f"Could not connect to the chatbot service: {e}")
        except Exception as e:
            st.error(f"An error occurred: {e}")
    else:
        st.warning("Please enter a prompt.")
