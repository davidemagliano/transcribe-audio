
import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Set page config
st.set_page_config(page_title="Audio Transcription App", layout="wide")

st.title("Audio Transcription with OpenAI")

# Get API key from environment variable
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    st.error("OpenAI API key not found. Please set the OPENAI_API_KEY environment variable.")
    st.stop()

client = OpenAI(api_key=api_key)

# --- UI Elements ---
uploaded_file = st.file_uploader("Upload an audio file", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])
model_choice = st.selectbox("Choose transcription model", ["gpt-4o-mini-transcribe", "gpt-4o-transcribe"], index=1)
prompt_text = st.text_area("Optional prompt for transcription context", value="You are a helpful assistant that transcribes audio files.")
transcribe_button = st.button("Transcribe Audio")

# --- Transcription Logic ---
if transcribe_button:
    if uploaded_file is not None:
        st.info("Transcription started...")

        # Display audio player
        st.audio(uploaded_file)

        try:
            # Use a placeholder for streamed output
            transcription_placeholder = st.empty()
            full_transcript = ""

            # Call the OpenAI API with streaming enabled
            stream = client.audio.transcriptions.create(
                model=model_choice,
                file=uploaded_file,
                response_format="text",
                prompt=prompt_text if prompt_text else None,
                stream=True
            )

            # Stream the transcription
            for event in stream:

                # # --- DEBUG ---
                # print(f"DEBUG: Received event type: {type(event)}")
                # try:
                #     print(f"DEBUG: Received event content: {event}")
                # except Exception as print_err:
                #     print(f"DEBUG: Could not print event directly: {print_err}")
                # # --- DEBUG ---
                
                # Check if it's a delta event containing text
                if event.type == 'transcript.text.delta' and event.delta:
                    full_transcript += event.delta
                    transcription_placeholder.markdown(
                        f"""**Transcription:**
```
{full_transcript}
```"""
                    )

            st.success("Transcription complete!")

        except Exception as e:
            st.error(f"An error occurred during transcription: {e}")

    else:
        st.warning("Please upload an audio file first.")

st.markdown("---")
st.markdown("Upload an audio file (up to 25MB), select a model, optionally provide a prompt, and click 'Transcribe Audio'.")
