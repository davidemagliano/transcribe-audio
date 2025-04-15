import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT # Import the prompt

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

# Initialize session state variables if they don't exist
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'edited_transcript' not in st.session_state:
    st.session_state.edited_transcript = None


# --- UI Elements ---
uploaded_file = st.file_uploader("Upload an audio file", type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"])
model_choice = st.selectbox("Choose transcription model", ["gpt-4o-mini-transcribe", "gpt-4o-transcribe"], index=1)
meeting_description = st.text_area("Optional description of the meeting", value="A conversation about ...")
transcribe_button = st.button("Transcribe Audio")

# --- Transcription Logic ---
if transcribe_button:
    if uploaded_file is not None:
        # Reset states for new transcription
        st.session_state.transcript = None # Clear previous transcript
        st.session_state.summary = None
        st.session_state.edited_transcript = None

        st.info("Transcription started...")

        # Display audio player
        st.audio(uploaded_file)

        # Use a placeholder for streamed output
        transcription_placeholder = st.empty()
        full_transcript = ""

        try:
            # Call the OpenAI API with streaming enabled
            stream = client.audio.transcriptions.create(
                model=model_choice,
                file=uploaded_file,
                response_format="text",
                prompt=f"You are listening to: {meeting_description}.",
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
                # Assuming the API sends events with a 'delta' attribute for text chunks
                # Adjust this check based on the actual structure of the stream events if necessary
                if hasattr(event, 'delta') and event.delta:
                    full_transcript += event.delta
                    transcription_placeholder.markdown(
                        f"""**Transcription:**
```
{full_transcript}
```"""
                    )


            # Store the final transcript in session state after streaming is complete
            st.session_state.transcript = full_transcript
            st.session_state.edited_transcript = full_transcript # Initialize editor content
            st.success("Transcription complete!")

        except Exception as e:
            st.error(f"An error occurred during transcription: {e}")
            # Ensure placeholders/states are cleared or handled on error
            transcription_placeholder.empty() # Clear the placeholder
            st.session_state.transcript = None # Reset state on error
            st.session_state.edited_transcript = None

    else:
        st.warning("Please upload an audio file first.")

# --- Display Transcript Editor and Summarization ---
# This section runs independently after the transcription button logic
if st.session_state.transcript is not None:
    st.markdown("---")
    st.subheader("Transcript")
    # Use a unique key for the text_area to prevent state issues
    st.session_state.edited_transcript = st.text_area(
        "Edit Transcript:",
        value=st.session_state.edited_transcript, # Bind to session state
        height=300,
        key="transcript_editor_area" # Unique key
    )

    generate_summary_button = st.button("Generate Summary")

    # --- Summarization Logic ---
    if generate_summary_button:
        if st.session_state.edited_transcript:
            st.info("Generating summary...")
            summary_placeholder = st.empty() # Placeholder for summary while generating
            try:
                # Prepare the prompt
                # Using a simple description; enhance as needed
                audio_description = f"Meeting description: {meeting_description}"
                formatted_prompt = SYSTEM_PROMPT.format(
                    audio_description=audio_description,
                    transcript=st.session_state.edited_transcript # Use potentially edited transcript
                )

                # Call Chat Completions API
                response = client.chat.completions.create(
                    model="gpt-4.1", # Or another suitable model like gpt-4o
                    messages=[
                        {"role": "system", "content": formatted_prompt},
                        {"role": "user", "content": "Please generate the meeting notes and key insights based on the provided transcript and context."}
                    ],
                    temperature=0.5,
                )
                st.session_state.summary = response.choices[0].message.content
                summary_placeholder.success("Summary generated!")

            except Exception as e:
                st.error(f"An error occurred during summary generation: {e}")
                summary_placeholder.empty() # Clear placeholder on error
                st.session_state.summary = None # Reset summary state
        else:
            st.warning("Transcript is empty. Cannot generate summary.")

# --- Display Summary ---
if st.session_state.summary is not None:
    st.markdown("---")
    st.subheader("Meeting Notes & Insights")
    st.markdown(st.session_state.summary)


st.markdown("---")
# Updated instructions reflecting the full workflow
st.markdown("1. Upload audio. 2. Click Transcribe. 3. Edit transcript (optional). 4. Click Generate Summary.")
