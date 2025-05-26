"""
Improved Audio Transcription App with better architecture and error handling.
"""
import streamlit as st
import math
from openai import OpenAI
from io import BytesIO

from config import config
from utils import (
    validate_audio_file, 
    preprocess_audio, 
    create_smart_chunks,
    transcribe_chunk,
    create_progress_bar,
    update_progress,
    estimate_processing_time,
    export_transcript,
    logger
)
from prompts import SYSTEM_PROMPT

# Set page config
st.set_page_config(
    page_title=config.ui.page_title,
    layout=config.ui.layout,
    page_icon="🎤"
)

st.title("🎤 Audio Transcription with OpenAI")
st.markdown("*Transform your audio into text and intelligent summaries*")
with st.container():
    st.markdown(
        """
        ### 📋 Workflow Summary
        **1.** Upload audio → **2.** Configure settings → **3.** Add context → **4.** Transcribe → **5.** Review & edit → **6.** Generate summary
        """
    ) 
st.markdown("---")

# Initialize OpenAI client
try:
    client = OpenAI(api_key=config.openai_api_key)
except Exception as e:
    st.error(f"Failed to initialize OpenAI client: {e}")
    st.stop()

# Initialize session state
def init_session_state():
    """Initialize session state variables."""
    defaults = {
        'transcript': None,
        'summary': None,
        'edited_transcript': None,
        'uploaded_file_name': None,
        'meeting_description_state': config.ui.default_description,
        'language_state': config.ui.default_language,
        'processing': False
    }
    
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value

init_session_state()

# Sidebar with settings
with st.sidebar:
    st.header("⚙️ Settings")
    
    # File size info
    st.info(f"📁 Max file size: {config.transcription.max_file_size_mb}MB")
    
    # Supported formats
    with st.expander("📋 Supported Formats"):
        st.write(", ".join(config.formats.upload_types))
    
    # Debug mode
    if config.debug:
        st.warning("🐛 Debug mode enabled")

# Step 1: Upload Section
st.header("1️⃣ Upload Audio File")
with st.container():
    col1, col2 = st.columns([3, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Choose an audio file",
            type=config.formats.upload_types,
            key="audio_uploader",
            help=f"Maximum file size: {config.transcription.max_file_size_mb}MB"
        )
        
        # File validation
        if uploaded_file:
            is_valid, error_msg = validate_audio_file(uploaded_file)
            if not is_valid:
                st.error(f"❌ {error_msg}")
                uploaded_file = None
            else:
                file_size_mb = len(uploaded_file.getvalue()) / (1024 * 1024)
                st.success(f"✅ {uploaded_file.name} ({file_size_mb:.1f}MB)")
    
    with col2:
        if uploaded_file:
            st.audio(uploaded_file)

st.markdown("---")

# Step 2: Configuration Section  
st.header("2️⃣ Configuration")
with st.container():
    col1, col2 = st.columns(2)
    
    with col1:
        model_choice = st.selectbox(
            "Transcription Model",
            ["gpt-4o-mini-transcribe", "gpt-4o-transcribe"],
            index=1 if config.ui.default_model == "gpt-4o-transcribe" else 0,
            help="Higher-tier models provide better accuracy"
        )
    
    with col2:
        st.session_state.language_state = st.selectbox(
            "Audio Language",
            options=config.language_options,
            index=config.language_options.index(st.session_state.language_state),
            format_func=config.get_language_display_name,
            key="language_select"
        )

st.markdown("---")

# Step 3: Context Section
st.header("3️⃣ Meeting Context (Optional)")
with st.container():
    st.session_state.meeting_description_state = st.text_area(
        "Describe the meeting content to improve transcription accuracy",
        value=st.session_state.meeting_description_state,
        placeholder="e.g., A team standup about product development...",
        key="meeting_desc_input",
        height=100,
        help="Providing context helps the AI understand technical terms and context"
    )

st.markdown("---")

# Step 4: Transcription Section
st.header("4️⃣ Start Transcription")

# Show file analysis if available
if uploaded_file and not st.session_state.processing:
    with st.expander("📊 File Analysis", expanded=False):
        try:
            audio_bytes = uploaded_file.getvalue()
            audio = preprocess_audio(audio_bytes)
            duration_seconds = len(audio) / 1000
            
            estimated_time = estimate_processing_time(duration_seconds)
            needs_chunking = duration_seconds > config.transcription.max_duration_seconds
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Duration", f"{duration_seconds:.1f}s")
            with col2:
                st.metric("Est. Processing", estimated_time)
            with col3:
                if needs_chunking:
                    num_chunks = math.ceil(duration_seconds / config.transcription.max_duration_seconds)
                    st.metric("Chunks", num_chunks)
                else:
                    st.metric("Chunks", "1")
                    
            if needs_chunking:
                st.info(f"ℹ️ File will be split into {num_chunks} chunks for processing")
                
        except Exception as e:
            logger.error(f"Error analyzing audio: {e}")
            st.warning("⚠️ Could not analyze audio file")

# Transcription button
with st.container():
    transcribe_button = st.button(
        "🚀 Start Transcription",
        disabled=uploaded_file is None or st.session_state.processing,
        type="primary",
        use_container_width=True
    )

if transcribe_button and uploaded_file:
    st.session_state.processing = True
    
    # Reset previous results
    st.session_state.transcript = None
    st.session_state.summary = None
    st.session_state.edited_transcript = None
    st.session_state.uploaded_file_name = uploaded_file.name
    
    try:
        with st.container():
            st.info("🔄 Processing audio...")
            
            # Preprocess audio
            audio_bytes = uploaded_file.getvalue()
            audio = preprocess_audio(audio_bytes)
            duration_seconds = len(audio) / 1000
            
            # Processing indicator
            st.balloons() if not st.session_state.processing else None
            
            # Determine processing strategy
            max_duration_ms = config.transcription.max_duration_seconds * 1000
            
            if len(audio) > max_duration_ms:
                # Chunked processing
                st.info(f"📊 Processing {duration_seconds:.1f}s audio in chunks...")
                
                chunks = create_smart_chunks(audio, max_duration_ms)
                progress_bar, status_text = create_progress_bar(len(chunks))
                
                transcript_parts = []
                previous_chunk_text = ""
                
                for i, chunk in enumerate(chunks):
                    update_progress(progress_bar, status_text, i, len(chunks), f"Transcribing chunk {i+1}")
                    
                    # Create context prompt
                    context_prompt = f"You are listening to: {st.session_state.meeting_description_state}. This is part {i+1} of {len(chunks)}."
                    if previous_chunk_text:
                        # Add context from previous chunk
                        context_words = ' '.join(previous_chunk_text.split()[-50:])
                        context_prompt += f" The previous part ended with: '{context_words}'"
                    
                    # Transcribe chunk
                    chunk_text = transcribe_chunk(
                        client=client,
                        chunk=chunk,
                        chunk_index=i,
                        total_chunks=len(chunks),
                        model=model_choice,
                        language=st.session_state.language_state,
                        context_prompt=context_prompt
                    )
                    
                    transcript_parts.append(chunk_text)
                    previous_chunk_text = chunk_text
                
                # Combine chunks
                full_transcript = " ".join(transcript_parts)
                update_progress(progress_bar, status_text, len(chunks), len(chunks), "Complete!")
                
            else:
                # Streaming processing for shorter files
                st.info("🔄 Streaming transcription...")
                
                temp_placeholder = st.empty()
                streamed_text = ""
                
                context_prompt = f"You are listening to: {st.session_state.meeting_description_state}."
                
                stream = client.audio.transcriptions.create(
                    model=model_choice,
                    file=uploaded_file,
                    response_format="text",
                    language=st.session_state.language_state if st.session_state.language_state != "auto" else None,
                    prompt=context_prompt,
                    stream=True
                )
                
                for event in stream:
                    chunk = ""
                    if hasattr(event, 'delta') and event.delta:
                        chunk = event.delta
                    elif hasattr(event, 'text') and event.text:
                        chunk = event.text
                    
                    if chunk:
                        streamed_text += chunk
                        temp_placeholder.markdown(f"**Live Transcription:**\n```\n{streamed_text}\n```")
                
                full_transcript = streamed_text
                temp_placeholder.empty()
            
            # Store results
            st.session_state.transcript = full_transcript.strip()
            st.session_state.edited_transcript = st.session_state.transcript
            
            st.success("✅ Transcription completed successfully!")
            logger.info(f"Transcription completed: {len(full_transcript)} characters")
            
    except Exception as e:
        st.error(f"❌ Transcription failed: {e}")
        logger.error(f"Transcription error: {e}")
        st.session_state.transcript = None
        st.session_state.edited_transcript = None
    
    finally:
        st.session_state.processing = False

# Step 5: Review & Edit Results
if st.session_state.transcript:
    st.markdown("---")
    st.header("5️⃣ Review & Edit Transcript")
    
    # Transcript display with actions
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.subheader("📄 Transcript Results")
        
        with col2:
            with st.expander("📥 Export Options"):
                export_format = st.selectbox("Format:", ["txt", "md"], key="export_format")
                if st.button("Download", key="download_transcript"):
                    export_data = export_transcript(st.session_state.transcript, export_format)
                    st.download_button(
                        label=f"Download {export_format.upper()}",
                        data=export_data,
                        file_name=f"transcript_{st.session_state.uploaded_file_name}.{export_format}",
                        mime="text/plain" if export_format == "txt" else "text/markdown"
                    )
    
    # Transcript content
    with st.expander("📖 View Full Transcript", expanded=True):
        st.code(st.session_state.transcript, language=None)
    
    # Transcript editor section
    st.subheader("✏️ Edit Transcript")
    with st.container():
        st.session_state.edited_transcript = st.text_area(
            "Make corrections before generating summary:",
            value=st.session_state.edited_transcript,
            height=250,
            key="transcript_editor",
            help="Edit the transcript to improve summary accuracy"
        )
    
    st.markdown("---")

# Step 6: Generate Summary
if st.session_state.edited_transcript:
    st.header("6️⃣ Generate AI Summary")
    
    with st.container():
        generate_summary_button = st.button(
            "✨ Generate Summary & Insights",
            type="primary",
            use_container_width=True,
            help="Create structured meeting notes and extract key insights"
        )
    
    if generate_summary_button:
        try:
            with st.spinner("🤖 Generating intelligent summary..."):
                audio_description = f"Meeting description: {st.session_state.meeting_description_state}"
                language_name = config.get_language_display_name(st.session_state.language_state)
                
                formatted_prompt = SYSTEM_PROMPT.format(
                    audio_description=audio_description,
                    transcript=st.session_state.edited_transcript,
                    language=language_name
                )
                
                response = client.chat.completions.create(
                    model=config.summary_model,
                    messages=[
                        {"role": "system", "content": formatted_prompt},
                        {"role": "user", "content": "Please generate the meeting notes and key insights based on the provided transcript and context."}
                    ],
                    temperature=0.5,
                )
                
                st.session_state.summary = response.choices[0].message.content
                st.success("✅ Summary generated successfully!")
                logger.info("Summary generated successfully")
                
        except Exception as e:
            st.error(f"❌ Summary generation failed: {e}")
            logger.error(f"Summary generation error: {e}")

# Results: Summary Display
if st.session_state.summary:
    st.markdown("---")
    st.header("✅ Summary & Insights")
    
    # Summary header with export
    col1, col2 = st.columns([3, 1])
    with col1:
        st.subheader("📊 AI-Generated Summary")
    with col2:
        with st.expander("📥 Export Summary"):
            if st.button("Download Summary", key="download_summary"):
                summary_data = st.session_state.summary.encode('utf-8')
                st.download_button(
                    label="Download MD",
                    data=summary_data,
                    file_name=f"summary_{st.session_state.uploaded_file_name}.md",
                    mime="text/markdown"
                )
    
    # Summary content
    with st.container():
        st.markdown(st.session_state.summary)