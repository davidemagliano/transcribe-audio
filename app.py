import streamlit as st
from openai import OpenAI
import os
from dotenv import load_dotenv
from prompts import SYSTEM_PROMPT
from pydub import AudioSegment # Import pydub
import math
from io import BytesIO # Import BytesIO

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

# --- Constants ---
MAX_DURATION_SECONDS = 600 # Max duration per chunk (10 minutes)

# Initialize session state variables if they don't exist
if 'transcript' not in st.session_state:
    st.session_state.transcript = None
if 'summary' not in st.session_state:
    st.session_state.summary = None
if 'edited_transcript' not in st.session_state:
    st.session_state.edited_transcript = None
if 'uploaded_file_name' not in st.session_state: # Store filename for context
    st.session_state.uploaded_file_name = None
if 'meeting_description_state' not in st.session_state:
    st.session_state.meeting_description_state = "A conversation about ..."
if 'language_state' not in st.session_state:
    st.session_state.language_state = "it" # Default to Italian

# --- UI Elements ---
uploaded_file = st.file_uploader(
    "Upload an audio file",
    type=["mp3", "mp4", "mpeg", "mpga", "m4a", "wav", "webm"],
    key="audio_uploader" # Add key for potential resets
)
model_choice = st.selectbox("Choose transcription model", ["gpt-4o-mini-transcribe", "gpt-4o-transcribe"], index=1)
st.session_state.meeting_description_state = st.text_area(
    "Optional description of the meeting",
    value=st.session_state.meeting_description_state,
    key="meeting_desc_input"
)
# Add language selection
st.session_state.language_state = st.selectbox(
    "Select Audio Language",
    options=["it", "en", "es", "fr", "de", "auto"], # Add more as needed, 'auto' might try detection but explicit is better
    index=["it", "en", "es", "fr", "de", "auto"].index(st.session_state.language_state), # Keep selection
    format_func=lambda x: {"it": "Italian", "en": "English", "es": "Spanish", "fr": "French", "de": "German", "auto": "Auto-detect"}.get(x, x),
    key="language_select"
)
transcribe_button = st.button("Transcribe Audio")

# Placeholders for dynamic UI updates
transcription_status_placeholder = st.empty()

# --- Transcription Logic ---
if transcribe_button:
    if uploaded_file is not None:
        # Reset states for new transcription
        st.session_state.transcript = None
        st.session_state.summary = None
        st.session_state.edited_transcript = None
        st.session_state.uploaded_file_name = uploaded_file.name
        transcription_status_placeholder.empty()

        st.info("Preparing audio...")
        st.audio(uploaded_file)
        
        full_transcript = "" # Initialize here

        try:
            # Load audio file with pydub
            audio_bytes = uploaded_file.getvalue()
            audio = AudioSegment.from_file(BytesIO(audio_bytes))
            
            # --- Prepend small silence --- 
            transcription_status_placeholder.info("Prepending small silence...")
            silence_duration_ms = 100 # Add 100ms of silence
            silence_segment = AudioSegment.silent(duration=silence_duration_ms)
            audio = silence_segment + audio
            # --- End prepending silence ---
            
            duration_seconds = len(audio) / 1000 # Update duration after adding silence

            # Check if splitting is needed
            if duration_seconds > MAX_DURATION_SECONDS:
                transcription_status_placeholder.info(f"Audio duration ({duration_seconds:.2f}s) exceeds limit. Splitting into chunks...")
                num_chunks = math.ceil(duration_seconds / MAX_DURATION_SECONDS)
                chunk_length_ms = MAX_DURATION_SECONDS * 1000
                
                transcript_parts = [] 
                previous_chunk_text = ""

                for i in range(num_chunks):
                    start_ms = i * chunk_length_ms
                    end_ms = min((i + 1) * chunk_length_ms, len(audio))
                    chunk = audio[start_ms:end_ms]

                    transcription_status_placeholder.info(f"Transcribing chunk {i+1}/{num_chunks}...")

                    # Export chunk to MP3 format
                    chunk_bytes_io = BytesIO()
                    chunk.export(chunk_bytes_io, format="mp3")
                    chunk_bytes_io.seek(0)

                    context_prompt = f"You are listening to: {st.session_state.meeting_description_state}. This is part {i+1} of {num_chunks}."
                    if previous_chunk_text:
                        context_prompt += f" The previous part ended with: '{' '.join(previous_chunk_text.split()[-50:])}'"

                    response_text = client.audio.transcriptions.create(
                        model=model_choice,
                        file=(f"chunk_{i+1}.mp3", chunk_bytes_io),
                        response_format="text",
                        language=st.session_state.language_state if st.session_state.language_state != "auto" else None,
                        prompt=context_prompt
                    )
                    
                    print(f"DEBUG: Chunk {i+1} response received (length {len(response_text)}):")
                    print(f"DEBUG: Chunk {i+1} START: {response_text[:100]}...")
                    print(f"DEBUG: Chunk {i+1} END: ...{response_text[-100:]}")
                    
                    current_chunk_text = str(response_text) if response_text is not None else ""
                    transcript_parts.append(current_chunk_text)
                    previous_chunk_text = current_chunk_text
                # --- (End of existing chunk processing logic) ---
                
                # Join parts after the loop
                full_transcript = " ".join(transcript_parts)

                print(f"DEBUG: Combined transcript length: {len(full_transcript)}")
                print(f"DEBUG: Combined transcript START: {full_transcript[:200]}...")
                print(f"DEBUG: Combined transcript END: ...{full_transcript[-200:]}")

            else:
                # Use streaming for shorter files
                transcription_status_placeholder.info("Transcription started (streaming)...")
                stream = client.audio.transcriptions.create(
                    model=model_choice,
                    file=uploaded_file,
                    response_format="text",
                    language=st.session_state.language_state if st.session_state.language_state != "auto" else None,
                    prompt=f"You are listening to: {st.session_state.meeting_description_state}.",
                    stream=True
                )
                
                # Use a temporary placeholder just for streaming output
                temp_stream_placeholder = st.empty()
                streamed_text = "" # Accumulate streamed text locally
                for event in stream:
                    chunk = ""
                    if hasattr(event, 'delta') and event.delta:
                        chunk = event.delta
                    elif hasattr(event, 'text') and event.text:
                        chunk = event.text

                    if chunk:
                        streamed_text += chunk
                        temp_stream_placeholder.markdown(
                            f"""**Transcription (Streaming):**
```
{streamed_text}
```"""
                        )
                full_transcript = streamed_text # Assign accumulated streamed text
                temp_stream_placeholder.empty() # Clear the temporary placeholder

            # --- Set session state AFTER successful transcription (chunked or streamed) ---
            st.session_state.transcript = full_transcript.strip()
            st.session_state.edited_transcript = st.session_state.transcript
            transcription_status_placeholder.success("Transcription complete!")
            # --- End setting session state ---

        except Exception as e:
            st.error(f"An error occurred during transcription: {e}")
            transcription_status_placeholder.empty()
            st.session_state.transcript = None
            st.session_state.edited_transcript = None
            st.session_state.uploaded_file_name = None

    else:
        st.warning("Please upload an audio file first.")

# --- Display Final Transcript, Editor and Summarization ---
if st.session_state.transcript is not None:
    st.markdown("---")
    st.subheader("Final Transcript")
    st.markdown(f"""
```
{st.session_state.transcript}
```
""")

    st.markdown("---")
    st.subheader("Edit Transcript & Generate Summary")
    st.session_state.edited_transcript = st.text_area(
        "Edit Transcript:",
        value=st.session_state.edited_transcript,
        height=300,
        key="transcript_editor_area"
    )

    generate_summary_button = st.button("Generate Summary")

    # --- Summarization Logic ---
    if generate_summary_button:
        if st.session_state.edited_transcript:
            st.info("Generating summary...")
            summary_placeholder = st.empty()
            try:
                audio_description = f"Meeting description: {st.session_state.meeting_description_state}"
                # Map language code to full name for the prompt
                language_map = {
                    "it": "Italian", "en": "English", "es": "Spanish", 
                    "fr": "French", "de": "German", "auto": "the language detected in the transcript"
                }
                selected_language_name = language_map.get(st.session_state.language_state, st.session_state.language_state)
                
                formatted_prompt = SYSTEM_PROMPT.format(
                    audio_description=audio_description,
                    transcript=st.session_state.edited_transcript,
                    language=selected_language_name # Pass the language name here
                )

                response = client.chat.completions.create(
                    model="gpt-4.1", # Use a powerful model for summarizing potentially long text
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
                summary_placeholder.empty()
                st.session_state.summary = None
        else:
            st.warning("Transcript is empty. Cannot generate summary.")

# --- Display Summary ---
if st.session_state.summary is not None:
    st.markdown("---")
    st.subheader("Meeting Notes & Insights")
    st.markdown(st.session_state.summary)

st.markdown("---")
st.markdown("1. Upload audio. 2. (Optional) Describe meeting. 3. Click Transcribe. 4. Edit transcript (optional). 5. Click Generate Summary.")
